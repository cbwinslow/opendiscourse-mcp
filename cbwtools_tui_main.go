// main.go - cbwtools TUI front-end
// =============================================================================
// Project       : cbwtools TUI
// Author        : cbwinslow (co-piloted by GPT-5.1 Thinking)
// Created       : 2025-11-19
// Summary       : Bubble Tea-based terminal UI for interacting with cbwtools.
//                 Uses the existing Python cbwtools CLI as a backend, calling
//                 it via os/exec to list and operate on secrets, bundles,
//                 shortcuts, repo aliases, folder aliases, and scripts.
//
// Inputs        : None directly; relies on environment variables.
//                 - CBWTOOLS_BIN (optional): path to cbwtools executable
//
// Outputs       : Terminal UI, stdout/stderr messages.
//
// Dependencies  :
//   Go modules:
//     - github.com/charmbracelet/bubbletea
//     - github.com/charmbracelet/bubbles/list
//     - github.com/charmbracelet/lipgloss
//
// Usage         :
//   go mod init github.com/youruser/cbwtools-tui
//   go get github.com/charmbracelet/bubbletea@latest
//   go get github.com/charmbracelet/bubbles@latest
//   go get github.com/charmbracelet/lipgloss@latest
//   go build -o cbwtools-tui
//   ./cbwtools-tui
//
// Notes         :
//   - This is a v1; it parses the text output from cbwtools list commands.
//     Later you can extend cbwtools to provide JSON output and switch this
//     UI to parse JSON instead.
//   - All actions are performed by invoking cbwtools; no secrets are stored
//     directly in this Go binary.
// =============================================================================

package main

import (
    "bytes"
    "context"
    "fmt"
    "os"
    "os/exec"
    "strings"
    "time"

    tea "github.com/charmbracelet/bubbletea"
    "github.com/charmbracelet/bubbles/list"
    "github.com/charmbracelet/lipgloss"
)

// -----------------------------------------------------------------------------
// Types & Enums
// -----------------------------------------------------------------------------

type section int

const (
    sectionSessions section = iota
    sectionDocker
    sectionSecrets
    sectionBundles
    sectionShortcuts
    sectionRepos
    sectionFolders
    sectionScripts
    sectionAI
    sectionCount
)

func (s section) String() string {
    switch s {
    case sectionSessions:
        return "Sessions"
    case sectionDocker:
        return "Docker"
    case sectionSecrets:
        return "Secrets"
    case sectionBundles:
        return "Bundles"
    case sectionShortcuts:
        return "Shortcuts"
    case sectionRepos:
        return "Repos"
    case sectionFolders:
        return "Folders"
    case sectionScripts:
        return "Scripts"
    case sectionAI:
        return "AI"
    default:
        return "Unknown"
    }
}

type entryType int

const (
    entrySession entryType = iota
    entryDocker
    entrySecret
    entryBundle
    entryShortcut
    entryRepo
    entryFolder
    entryScript
    entryAI
)

// listItem implements list.Item from Bubbles.

type listItem struct {
    title string
    desc  string
    kind  entryType
}

func (i listItem) Title() string       { return i.title }
func (i listItem) Description() string { return i.desc }
func (i listItem) FilterValue() string { return i.title }

// Messages

type errMsg struct{ err error }

func (e errMsg) Error() string { return e.err.Error() }

type loadedItemsMsg struct {
    section section
    items   []list.Item
}

// -----------------------------------------------------------------------------
// Model
// -----------------------------------------------------------------------------

type model struct {
    section section
    list    list.Model

    status  string
    loading bool
    width   int
    height  int
}

// -----------------------------------------------------------------------------
// Styling
// -----------------------------------------------------------------------------

var (
    titleStyle  = lipgloss.NewStyle().Bold(true).Foreground(lipgloss.Color("205"))
    statusStyle = lipgloss.NewStyle().Foreground(lipgloss.Color("241"))
    activeTab   = lipgloss.NewStyle().Bold(true).Foreground(lipgloss.Color("86"))
    inactiveTab = lipgloss.NewStyle().Foreground(lipgloss.Color("240"))
    borderStyle = lipgloss.NewStyle().Border(lipgloss.NormalBorder()).Padding(0, 1)
    helpStyle   = lipgloss.NewStyle().Foreground(lipgloss.Color("244"))
)

// -----------------------------------------------------------------------------
// Backend helpers: locating cbwtools
// -----------------------------------------------------------------------------

func cbwtoolsBin() string {
    if v := os.Getenv("CBWTOOLS_BIN"); v != "" {
        return v
    }
    // Assumes cbwtools is on PATH; you can also point this to cbwtools.py
    return "cbwtools"
}

// runCbwtools runs cbwtools with the given args and returns stdout as string.
// It uses a context with a reasonable timeout to avoid hanging the UI.

func runCbwtools(args ...string) (string, error) {
    ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
    defer cancel()

    cmd := exec.CommandContext(ctx, cbwtoolsBin(), args...)
    cmd.Env = os.Environ()
    out, err := cmd.CombinedOutput()
    if ctx.Err() == context.DeadlineExceeded {
        return "", fmt.Errorf("cbwtools timeout")
    }
    if err != nil {
        return "", fmt.Errorf("cbwtools error: %w: %s", err, strings.TrimSpace(string(out)))
    }
    return string(out), nil
}

// -----------------------------------------------------------------------------
// tmux helpers
// -----------------------------------------------------------------------------

type tmuxSession struct {
    Name string
    Info string
}

func tmuxAvailable() bool {
    _, err := exec.LookPath("tmux")
    return err == nil
}

// listTmuxSessions returns a list of tmux sessions. If tmux is installed but
// no server is running, it returns an empty slice.
func listTmuxSessions() ([]tmuxSession, error) {
    cmd := exec.Command("tmux", "list-sessions", "-F", "#S:#I:#W:#{session_windows}")
    var out bytes.Buffer
    cmd.Stdout = &out
    cmd.Stderr = &out
    if err := cmd.Run(); err != nil {
        // When no sessions exist, tmux exits non-zero with a friendly message.
        if strings.Contains(out.String(), "failed to connect") ||
            strings.Contains(out.String(), "no server running") {
            return []tmuxSession{}, nil
        }
        return nil, fmt.Errorf("tmux list error: %v (%s)", err, strings.TrimSpace(out.String()))
    }

    var sessions []tmuxSession
    for _, line := range strings.Split(out.String(), "
") {
        line = strings.TrimSpace(line)
        if line == "" {
            continue
        }
        parts := strings.SplitN(line, ":", 2)
        name := parts[0]
        info := ""
        if len(parts) > 1 {
            info = parts[1]
        }
        sessions = append(sessions, tmuxSession{Name: name, Info: info})
    }
    return sessions, nil
}

// attachTmuxSession attaches to a tmux session. This will take over the
// terminal until the user detaches.
func attachTmuxSession(name string) error {
    cmd := exec.Command("tmux", "attach", "-t", name)
    cmd.Stdout = os.Stdout
    cmd.Stderr = os.Stderr
    cmd.Stdin = os.Stdin
    return cmd.Run()
}

func newTmuxSession(name string) error {
    cmd := exec.Command("tmux", "new-session", "-d", "-s", name)
    cmd.Stdout = os.Stdout
    cmd.Stderr = os.Stderr
    return cmd.Run()
}

func killTmuxSession(name string) error {
    cmd := exec.Command("tmux", "kill-session", "-t", name)
    cmd.Stdout = os.Stdout
    cmd.Stderr = os.Stderr
    return cmd.Run()
}

// -----------------------------------------------------------------------------
// Docker helpers
// -----------------------------------------------------------------------------

type dockerContainer struct {
    ID     string
    Image  string
    Name   string
    Status string
}

func dockerAvailable() bool {
    _, err := exec.LookPath("docker")
    return err == nil
}

func listDockerContainers() ([]dockerContainer, error) {
    cmd := exec.Command("docker", "ps", "-a", "--format", "{{.ID}}	{{.Image}}	{{.Names}}	{{.Status}}")
    out, err := cmd.Output()
    if err != nil {
        return nil, fmt.Errorf("docker ps error: %w", err)
    }

    var containers []dockerContainer
    for _, line := range strings.Split(string(out), "
") {
        if strings.TrimSpace(line) == "" {
            continue
        }
        parts := strings.Split(line, "	")
        if len(parts) < 4 {
            continue
        }
        containers = append(containers, dockerContainer{
            ID:     parts[0],
            Image:  parts[1],
            Name:   parts[2],
            Status: parts[3],
        })
    }
    return containers, nil
}

func dockerStart(name string) error {
    cmd := exec.Command("docker", "start", name)
    cmd.Stdout = os.Stdout
    cmd.Stderr = os.Stderr
    return cmd.Run()
}

func dockerStop(name string) error {
    cmd := exec.Command("docker", "stop", name)
    cmd.Stdout = os.Stdout
    cmd.Stderr = os.Stderr
    return cmd.Run()
}

// -----------------------------------------------------------------------------
// Parsing helpers
// -----------------------------------------------------------------------------

// parseName extracts the logical name from a list line.
// Examples:
//   "  - openai/api_key (created: 2025...)"         -> "openai/api_key"
//   "  - install/dev-env: scripts/path (lang=...)" -> "install/dev-env"
//   "  - opendiscourse: https://..."               -> "opendiscourse"
func parseName(line string) string {
    line = strings.TrimSpace(line)
    if !strings.HasPrefix(line, "- ") {
        return ""
    }
    line = strings.TrimPrefix(line, "- ")

    // Prefer colon delimiter
    if idx := strings.Index(line, ":"); idx != -1 {
        return strings.TrimSpace(line[:idx])
    }
    // Fallback: stop at first " ("
    if idx := strings.Index(line, " ("); idx != -1 {
        return strings.TrimSpace(line[:idx])
    }
    return strings.TrimSpace(line)
}

// -----------------------------------------------------------------------------
// Section loaders
// -----------------------------------------------------------------------------

// fetchSectionItems uses cbwtools list-* commands (and tmux/docker CLIs) to build list items.
func fetchSectionItems(s section) ([]list.Item, error) {
    var (
        out string
        err error
    )

    switch s {
    case sectionSessions:
        if !tmuxAvailable() {
            return []list.Item{
                listItem{
                    title: "(tmux not found)",
                    desc:  "Install tmux to use session management.",
                    kind:  entrySession,
                },
            }, nil
        }
        sessions, err := listTmuxSessions()
        if err != nil {
            return nil, err
        }
        if len(sessions) == 0 {
            return []list.Item{
                listItem{
                    title: "(no tmux sessions)",
                    desc:  "Press 'n' to create a new tmux session.",
                    kind:  entrySession,
                },
            }, nil
        }
        items := make([]list.Item, 0, len(sessions))
        for _, sess := range sessions {
            desc := fmt.Sprintf("tmux session %s %s", sess.Name, sess.Info)
            items = append(items, listItem{title: sess.Name, desc: desc, kind: entrySession})
        }
        return items, nil

    case sectionDocker:
        if !dockerAvailable() {
            return []list.Item{
                listItem{
                    title: "(docker not found)",
                    desc:  "Install Docker to manage containers.",
                    kind:  entryDocker,
                },
            }, nil
        }
        containers, err := listDockerContainers()
        if err != nil {
            return nil, err
        }
        if len(containers) == 0 {
            return []list.Item{
                listItem{
                    title: "(no containers)",
                    desc:  "Use docker CLI to create containers, then reload.",
                    kind:  entryDocker,
                },
            }, nil
        }
        items := make([]list.Item, 0, len(containers))
        for _, c := range containers {
            desc := fmt.Sprintf("%s (%s) - %s", c.Name, c.Image, c.Status)
            items = append(items, listItem{title: c.Name, desc: desc, kind: entryDocker})
        }
        return items, nil

    case sectionSecrets:
        out, err = runCbwtools("list-secrets")
    case sectionBundles:
        out, err = runCbwtools("list-bundles")
    case sectionShortcuts:
        out, err = runCbwtools("list-shortcuts")
    case sectionRepos:
        out, err = runCbwtools("list-repo-aliases")
    case sectionFolders:
        out, err = runCbwtools("list-folder-aliases")
    case sectionScripts:
        out, err = runCbwtools("list-scripts")
    case sectionAI:
        // For now, AI section is static options. Later we can query a config.
        items := []list.Item{
            listItem{
                title: "OpenRouter Chat", 
                desc:  "Launch cbwtools-ai chat using OpenRouter (requires cbwtools-ai helper and tmux).",
                kind:  entryAI,
            },
            listItem{
                title: "Gemini Chat",
                desc:  "Launch cbwtools-ai chat using Gemini (requires cbwtools-ai helper and tmux).",
                kind:  entryAI,
            },
        }
        return items, nil

    default:
        return nil, fmt.Errorf("unknown section")
    }

    if err != nil {
        return nil, err
    }

    var items []list.Item
    lines := strings.Split(out, "
")
    for _, line := range lines {
        if strings.HasPrefix(strings.TrimSpace(line), "- ") {
            name := parseName(line)
            if name == "" {
                continue
            }
            li := listItem{title: name, desc: strings.TrimSpace(line), kind: entryFromSection(s)}
            items = append(items, li)
        }
    }

    if len(items) == 0 {
        items = append(items, listItem{title: "(none)", desc: "No items found in this section.", kind: entryFromSection(s)})
    }

    return items, nil
}

func entryFromSection(s section) entryType {
    switch s {
    case sectionSessions:
        return entrySession
    case sectionDocker:
        return entryDocker
    case sectionSecrets:
        return entrySecret
    case sectionBundles:
        return entryBundle
    case sectionShortcuts:
        return entryShortcut
    case sectionRepos:
        return entryRepo
    case sectionFolders:
        return entryFolder
    case sectionScripts:
        return entryScript
    case sectionAI:
        return entryAI
    default:
        return entrySecret
    }
}

// -----------------------------------------------------------------------------
// Bubble Tea init/update/view
// -----------------------------------------------------------------------------

func initialModel() model {
    const defaultWidth = 80
    const defaultHeight = 24

    l := list.New([]list.Item{}, list.NewDefaultDelegate(), defaultWidth-4, defaultHeight-5)
    l.Title = "cbwtools"
    l.SetShowStatusBar(false)
    l.SetFilteringEnabled(true)

    m := model{
        section: sectionSessions,
        list:    l,
        status:  "Loading tmux sessions...",
        loading: true,
        width:   defaultWidth,
        height:  defaultHeight,
    }

    return m
}

func (m model) Init() tea.Cmd {
    return loadSectionCmd(m.section)
}

func loadSectionCmd(s section) tea.Cmd {
    return func() tea.Msg {
        items, err := fetchSectionItems(s)
        if err != nil {
            return errMsg{err}
        }
        return loadedItemsMsg{section: s, items: items}
    }
}

func (m model) Update(msg tea.Msg) (tea.Model, tea.Cmd) {
    var cmds []tea.Cmd

    switch msg := msg.(type) {
    case tea.KeyMsg:
        switch msg.String() {
        case "ctrl+c", "q":
            return m, tea.Quit

        // Section switching
        case "tab":
            m.section = (m.section + 1) % sectionCount
            m.status = fmt.Sprintf("Switched to %s", m.section)
            m.loading = true
            return m, loadSectionCmd(m.section)
        case "shift+tab":
            if m.section == 0 {
                m.section = sectionCount - 1
            } else {
                m.section--
            }
            m.status = fmt.Sprintf("Switched to %s", m.section)
            m.loading = true
            return m, loadSectionCmd(m.section)
        case "s":
            m.section = sectionSessions
            m.status = "Switched to Sessions"
            m.loading = true
            return m, loadSectionCmd(m.section)
        case "d":
            m.section = sectionDocker
            m.status = "Switched to Docker"
            m.loading = true
            return m, loadSectionCmd(m.section)
        case "c":
            m.section = sectionSecrets
            m.status = "Switched to Secrets"
            m.loading = true
            return m, loadSectionCmd(m.section)
        case "a":
            m.section = sectionAI
            m.status = "Switched to AI"
            m.loading = true
            return m, loadSectionCmd(m.section)

        // Reload current section
        case "r":
            m.status = fmt.Sprintf("Reloading %s...", m.section)
            m.loading = true
            return m, loadSectionCmd(m.section)

        // Create/kill tmux sessions from Sessions tab
        case "n":
            if m.section == sectionSessions && tmuxAvailable() {
                // Simple new session name based on timestamp; for now we don't prompt.
                name := fmt.Sprintf("cbw-%d", time.Now().Unix())
                if err := newTmuxSession(name); err != nil {
                    m.status = fmt.Sprintf("Failed to create tmux session: %v", err)
                } else {
                    m.status = fmt.Sprintf("Created tmux session '%s'", name)
                }
                return m, loadSectionCmd(m.section)
            }
        case "k":
            if m.section == sectionSessions {
                if sel, ok := m.list.SelectedItem().(listItem); ok && sel.title != "" && !strings.HasPrefix(sel.title, "(") {
                    if err := killTmuxSession(sel.title); err != nil {
                        m.status = fmt.Sprintf("Failed to kill tmux session '%s': %v", sel.title, err)
                    } else {
                        m.status = fmt.Sprintf("Killed tmux session '%s'", sel.title)
                    }
                    return m, loadSectionCmd(m.section)
                }
            }

        case "enter":
            // Perform default action based on entry type
            if sel, ok := m.list.SelectedItem().(listItem); ok {
                return m.handleEnter(sel)
            }
        }

    case tea.WindowSizeMsg:
        m.width = msg.Width
        m.height = msg.Height
        m.list.SetSize(msg.Width-4, msg.Height-5)

    case loadedItemsMsg:
        if msg.section == m.section {
            m.list.SetItems(msg.items)
            m.loading = false
            m.status = fmt.Sprintf("Loaded %d items from %s", len(msg.items), m.section)
        }

    case errMsg:
        m.status = fmt.Sprintf("Error: %v", msg.err)
        m.loading = false
    }

    var cmd tea.Cmd
    m.list, cmd = m.list.Update(msg)
    cmds = append(cmds, cmd)

    return m, tea.Batch(cmds...)
}

func (m model) handleEnter(it listItem) (tea.Model, tea.Cmd) {
    name := it.title

    switch it.kind {
    case entrySession:
        if !tmuxAvailable() {
            m.status = "tmux is not installed."
            return m, nil
        }
        // Attach to session; this will effectively leave the TUI until user detaches.
        fmt.Printf("
Attaching to tmux session '%s'... (detach with Ctrl-b d)
", name)
        if err := attachTmuxSession(name); err != nil {
            fmt.Fprintf(os.Stderr, "tmux attach error: %v
", err)
            m.status = fmt.Sprintf("Failed to attach to tmux session '%s'", name)
        } else {
            m.status = fmt.Sprintf("Detached from tmux session '%s'", name)
        }

    case entryDocker:
        if !dockerAvailable() {
            m.status = "Docker is not installed."
            return m, nil
        }
        // Toggle start/stop based on status text.
        descLower := strings.ToLower(it.desc)
        go func(containerName string, desc string) {
            if strings.Contains(descLower, "up ") {
                fmt.Printf("
Stopping container '%s'...
", containerName)
                if err := dockerStop(containerName); err != nil {
                    fmt.Fprintf(os.Stderr, "docker stop error: %v
", err)
                } else {
                    fmt.Printf("Container '%s' stopped.
", containerName)
                }
            } else {
                fmt.Printf("
Starting container '%s'...
", containerName)
                if err := dockerStart(containerName); err != nil {
                    fmt.Fprintf(os.Stderr, "docker start error: %v
", err)
                } else {
                    fmt.Printf("Container '%s' started.
", containerName)
                }
            }
        }(name, it.desc)
        m.status = fmt.Sprintf("Toggled container '%s' (check status with 'r').", name)

    case entrySecret:
        // Show secret value using cbwtools get-secret --raw
        go func() {
            out, err := runCbwtools("get-secret", name, "--raw")
            if err != nil {
                fmt.Fprintf(os.Stderr, "get-secret error: %v
", err)
                return
            }
            fmt.Printf("
%s = %s
", name, strings.TrimSpace(out))
        }()
        m.status = fmt.Sprintf("Fetched secret '%s' (printed to stdout).", name)

    case entryShortcut:
        go func() {
            fmt.Printf("
Running shortcut '%s'...
", name)
            _, err := runCbwtools("run-shortcut", name, "--yes")
            if err != nil {
                fmt.Fprintf(os.Stderr, "run-shortcut error: %v
", err)
            }
        }()
        m.status = fmt.Sprintf("Triggered shortcut '%s' via cbwtools.", name)

    case entryScript:
        go func() {
            fmt.Printf("
Running script '%s'...
", name)
            _, err := runCbwtools("run-script", name, "--yes")
            if err != nil {
                fmt.Fprintf(os.Stderr, "run-script error: %v
", err)
            }
        }()
        m.status = fmt.Sprintf("Triggered script '%s' via cbwtools.", name)

    case entryRepo:
        // For repos, default action: clone-repo-alias into configured or cwd/<name>
        go func() {
            fmt.Printf("
Cloning repo alias '%s'...
", name)
            _, err := runCbwtools("clone-repo-alias", name)
            if err != nil {
                fmt.Fprintf(os.Stderr, "clone-repo-alias error: %v
", err)
            }
        }()
        m.status = fmt.Sprintf("Triggered clone for repo alias '%s'.", name)

    case entryFolder:
        // For folders, just print a hint line to stdout
        fmt.Printf("
Folder alias '%s' selected (see cbwtools list-folder-aliases for path).
", name)
        m.status = fmt.Sprintf("Selected folder alias '%s'.", name)

    case entryBundle:
        fmt.Printf("
Use cbwtools save-folder-bundle / fetch-folder-bundle to manage bundles.
")
        m.status = "Bundle selected (no default TUI action yet)."

    case entryAI:
        // For now we assume a helper named `cbwtools-ai` exists and tmux is available.
        if !tmuxAvailable() {
            fmt.Printf("
AI chat helpers expect tmux; please install tmux first.
")
            m.status = "tmux is required for AI chat helper."
            return m, nil
        }
        // Decide provider based on title.
        var provider string
        switch name {
        case "OpenRouter Chat":
            provider = "openrouter"
        case "Gemini Chat":
            provider = "gemini"
        default:
            provider = "openrouter"
        }
        // Start/attach an AI chat tmux session so you can keep conversations around.
        sessionName := fmt.Sprintf("ai-%s", provider)
        go func() {
            fmt.Printf("
Launching AI chat (provider=%s) in tmux session '%s'...
", provider, sessionName)
            // We use `tmux new-session -A` to create or attach.
            cmd := exec.Command("tmux", "new-session", "-A", "-s", sessionName, "cbwtools-ai", "chat", "--provider", provider)
            cmd.Stdout = os.Stdout
            cmd.Stderr = os.Stderr
            cmd.Stdin = os.Stdin
            if err := cmd.Run(); err != nil {
                fmt.Fprintf(os.Stderr, "AI chat helper error: %v
", err)
            }
        }()
        m.status = fmt.Sprintf("AI chat (provider=%s) launched/attached in tmux.", provider)
    }

    return m, nil
}

// -----------------------------------------------------------------------------
// View
// -----------------------------------------------------------------------------

func (m model) View() string {
    if m.width == 0 || m.height == 0 {
        return "Loading..."
    }

    // Tabs
    var tabs []string
    for s := section(0); s < sectionCount; s++ {
        if s == m.section {
            tabs = append(tabs, activeTab.Render(s.String()))
        } else {
            tabs = append(tabs, inactiveTab.Render(s.String()))
        }
    }

    header := titleStyle.Render("cbwtools TUI") + "  " + strings.Join(tabs, " | ")

    content := m.list.View()

    help := helpStyle.Render("tab/shift+tab: cycle • s: sessions • d: docker • c: secrets • a: AI • r: reload • n/k: new/kill session • enter: action • q: quit")
    status := statusStyle.Render(m.status)

    joined := fmt.Sprintf("%s
%s

%s
%s", header, borderStyle.Render(content), status, help)
    return joined
}

// -----------------------------------------------------------------------------
// Main
// -----------------------------------------------------------------------------

func main() {
    p := tea.NewProgram(initialModel(), tea.WithAltScreen())
    if _, err := p.Run(); err != nil {
        fmt.Fprintf(os.Stderr, "Error running program: %v
", err)
        os.Exit(1)
    }
}
