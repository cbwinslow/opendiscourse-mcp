# Automated Code Analysis & Security Workflows

This repository includes a comprehensive suite of automated workflows for code analysis, security scanning, and quality assurance. All workflows are designed as generic templates that can be adapted for other projects.

## 🚀 Available Workflows

### Secrets Management

#### 0. **Fetch Secrets from Bitwarden** (`fetch-secrets.yml`)
- **Purpose**: Reusable workflow to securely retrieve secrets from Bitwarden
- **Type**: Reusable workflow (called by other workflows)
- **Features**:
  - Bitwarden CLI integration
  - Secure secret retrieval
  - Centralized secrets management
  - No secrets stored in GitHub

### Core Analysis Workflows

#### 1. **CI/CD Pipeline** (`ci.yml`)
- **Purpose**: Main CI/CD pipeline with testing, linting, and deployment
- **Triggers**: Push/PR to main/develop, scheduled daily
- **Features**:
  - Multi-Python version testing (3.9, 3.10, 3.11)
  - PostgreSQL + Redis services for integration tests
  - Code formatting (Black, isort)
  - Linting (flake8)
  - Type checking (mypy)
  - Security scanning (Bandit, Safety)
  - Test coverage reporting
  - Staging/production deployment

#### 2. **Code Quality Dashboard** (`code-quality-dashboard.yml`)
- **Purpose**: Orchestrates all analysis tools and generates comprehensive reports
- **Triggers**: Push/PR, scheduled daily, manual
- **Features**:
  - Quick quality checks (formatting, linting, security)
  - Comprehensive analysis (optional full suite)
  - HTML dashboard generation
  - PR comments with key metrics
  - Workflow summary reports

#### 3. **Multi-Tool Analysis** (`multi-tool-analysis.yml`)
- **Purpose**: Runs multiple analysis tools in parallel
- **Triggers**: Push/PR, weekly schedule
- **Tools**:
  - Static analysis (flake8, pylint, mypy, bandit, safety, radon)
  - Dependency analysis (pipdeptree, pip-audit)
  - Container analysis (Trivy, Dive) - if Dockerfile exists
  - Performance analysis (pytest-benchmark, memory profiling)
  - Coverage analysis (pytest-cov)

### Security & Vulnerability Scanning

#### 4. **CodeQL Analysis** (`codeql-analysis.yml`)
- **Purpose**: GitHub's built-in security and quality analysis
- **Languages**: Python, JavaScript (configurable)
- **Features**: Advanced security queries, SARIF upload to GitHub Security tab

#### 5. **Snyk Security Scan** (`snyk-security.yml`)
- **Purpose**: Dependency vulnerability scanning and container security
- **Features**:
  - Python dependency scanning
  - Container image scanning (if Dockerfile exists)
  - SARIF results for GitHub Security tab

#### 6. **Comprehensive Security** (`comprehensive-security.yml`)
- **Purpose**: Multiple security tools working together
- **Tools**:
  - Bandit (Python security)
  - Safety (dependency vulnerabilities)
  - Semgrep (semantic code analysis)
  - Trivy (container/filesystem scanning)
  - OWASP ZAP (web app scanning - optional)

#### 7. **Qono Security** (`qono-security.yml`)
- **Purpose**: Advanced security analysis with policy enforcement
- **Features**: Custom security policies, compliance checking

#### 8. **Red Hat Dependency Analytics** (`redhat-dependency-analytics.yml`)
- **Purpose**: Red Hat's dependency analysis and license compliance
- **Features**: SBOM generation, vulnerability analysis, license checking

### Code Quality & AI Analysis

#### 9. **Codacy Analysis** (`codacy-analysis.yml`)
- **Purpose**: Code quality and maintainability analysis
- **Features**: Dashboard integration, PR analysis, coverage reporting

#### 10. **CodeRabbitAI Review** (`coderabbitai-review.yml`)
- **Purpose**: AI-powered code review and suggestions
- **Features**: Automated PR reviews, customizable prompts

#### 11. **AI Code Analysis** (`ai-code-analysis.yml`)
- **Purpose**: AI-powered code improvement suggestions
- **Features**:
  - OpenAI GPT analysis
  - Claude analysis (optional)
  - Automated code suggestions

#### 12. **Automated Code Fixes** (`automated-code-fixes.yml`)
- **Purpose**: Automatically apply code formatting and fixes
- **Features**:
  - Black/isort formatting
  - autopep8 fixes
  - Security fix suggestions
  - Performance optimization recommendations
  - Automated PR creation

### Documentation & Maintenance

#### 13. **Automated Documentation** (`automated-documentation.yml`)
- **Purpose**: Generate and update documentation from code
- **Features**:
  - Sphinx documentation generation
  - MkDocs site building
  - API documentation (pdoc)
  - Dependency documentation
  - Code metrics documentation
  - GitHub Pages deployment
  - Wiki updates

## 🔧 Configuration

### Bitwarden Secrets Management

This workflow suite now uses Bitwarden for secure secrets management. Instead of storing API tokens directly in GitHub repository secrets, they are retrieved from your Bitwarden vault during workflow execution.

#### Setup Bitwarden Integration

1. **Install Bitwarden CLI** (if not already done)
2. **Create a Bitwarden account** or use your existing one
3. **Store your secrets** in Bitwarden with these paths:
   ```
   op://private/snyk/token
   op://private/sonarqube/token
   op://private/sonarqube/host_url
   op://private/codacy/api_token
   op://private/codacy/project_token
   op://private/openai/api_key
   op://private/qono/api_key
   op://private/redhat/api_key
   op://private/slack/webhook
   ```
4. **Add Bitwarden credentials to GitHub secrets**:
   ```bash
   BW_USERNAME=your_bitwarden_email
   BW_PASSWORD=your_bitwarden_master_password
   BW_HOST=https://vault.bitwarden.com  # (optional, defaults to bitwarden.com)
   ```

#### How It Works

- The `fetch-secrets.yml` reusable workflow logs into Bitwarden and retrieves all required secrets
- Individual workflows call this reusable workflow to get their needed secrets
- Secrets are never stored in GitHub - they're fetched fresh each run
- This provides enhanced security and centralized secret management

### Required Secrets (GitHub Repository Settings)

Only the Bitwarden credentials need to be stored in GitHub secrets:

```bash
# Bitwarden credentials for secret retrieval
BW_USERNAME=your_bitwarden_email
BW_PASSWORD=your_bitwarden_master_password
BW_HOST=https://vault.bitwarden.com  # Optional

# Note: All other secrets (Snyk, SonarQube, etc.) are now retrieved from Bitwarden
```

### Dependabot Configuration

The `dependabot.yml` file configures automatic dependency updates:

- **Python**: Weekly updates on Mondays
- **GitHub Actions**: Weekly updates on Mondays
- **Docker**: Weekly updates (if applicable)
- **Frontend**: Weekly updates for docs (if applicable)

### Workflow Customization

Each workflow is designed as a template. To adapt for your project:

1. **Update file paths**: Change `mcp_server` to your main package name
2. **Modify Python versions**: Adjust matrix strategies as needed
3. **Configure tools**: Update tool-specific configurations
4. **Add/remove tools**: Comment out or modify sections as needed
5. **Update triggers**: Adjust when workflows run based on your needs
6. **Bitwarden Integration**: 
   - Update the `op://` paths in `fetch-secrets.yml` to match your Bitwarden vault structure
   - Modify the secrets retrieved based on your needs
   - Add the fetch-secrets job to any new workflows that require API tokens

#### Adapting Workflows to Use Bitwarden

To integrate Bitwarden secrets into existing or new workflows:

1. Add a job that calls the fetch-secrets workflow:
   ```yaml
   fetch-secrets-job:
     uses: ./.github/workflows/fetch-secrets.yml
     secrets:
       BW_USERNAME: ${{ secrets.BW_USERNAME }}
       BW_PASSWORD: ${{ secrets.BW_PASSWORD }}
       BW_HOST: ${{ secrets.BW_HOST }}
   ```

2. Make other jobs depend on it and use the outputs:
   ```yaml
   my-job:
     needs: fetch-secrets-job
     env:
       MY_TOKEN: ${{ needs.fetch-secrets-job.outputs.my_token }}
   ```

3. Update the secrets in Bitwarden and the paths in `fetch-secrets.yml`

## 📊 Dashboard & Reporting

### Quality Dashboard

The main dashboard (`code-quality-dashboard.yml`) provides:

- **Test Coverage**: Percentage with color coding
- **Security Issues**: Count from various scanners
- **Code Complexity**: Analysis of complex functions
- **Performance Metrics**: Benchmark results
- **Recommendations**: Actionable improvement suggestions

### Artifacts

All workflows generate artifacts that can be downloaded:

- `quality-dashboard`: HTML dashboard
- `security-scan-results`: Security scan outputs
- `performance-analysis`: Performance metrics
- `coverage-reports`: Test coverage data
- `generated-docs`: Auto-generated documentation
- `ai-analysis-results`: AI suggestions

## 🚦 Workflow Status

### Quick Reference

| Workflow | Purpose | Frequency | Duration |
|----------|---------|-----------|----------|
| CI/CD Pipeline | Testing & Deployment | Push/PR + Daily | 10-15 min |
| Code Quality Dashboard | Overview Report | Push/PR + Daily | 5-10 min |
| Multi-Tool Analysis | Deep Analysis | Weekly | 15-30 min |
| Security Scans | Vulnerability Checks | Daily/Weekly | 5-15 min |
| AI Analysis | Code Suggestions | Weekly | 5-10 min |
| Documentation | Auto-docs | Weekly | 5-10 min |

### Status Badges

Add these badges to your README:

```markdown
[![CI/CD Pipeline](https://github.com/cbwinslow/opendiscourse-mcp/workflows/CI/CD%20Pipeline/badge.svg)](https://github.com/cbwinslow/opendiscourse-mcp/actions)
[![CodeQL](https://github.com/cbwinslow/opendiscourse-mcp/workflows/CodeQL%20Analysis/badge.svg)](https://github.com/cbwinslow/opendiscourse-mcp/actions)
[![Snyk](https://github.com/cbwinslow/opendiscourse-mcp/workflows/Snyk%20Security%20Scan/badge.svg)](https://github.com/cbwinslow/opendiscourse-mcp/actions)
[![Codacy](https://api.codacy.com/project/badge/Grade/your_codacy_id)](https://www.codacy.com/gh/cbwinslow/opendiscourse-mcp)
[![SonarCloud](https://sonarcloud.io/api/project_badges/measure?project=cbwinslow_opendiscourse-mcp&metric=alert_status)](https://sonarcloud.io/dashboard?id=cbwinslow_opendiscourse-mcp)
```

## 🔄 Maintenance

### Regular Tasks

1. **Review Security Alerts**: Check GitHub Security tab weekly
2. **Update Dependencies**: Monitor Dependabot PRs
3. **Review AI Suggestions**: Check AI analysis artifacts
4. **Update Tool Configurations**: Keep analysis tools current
5. **Monitor Performance**: Review benchmark results

### Troubleshooting

- **Workflow Failures**: Check the Actions tab for detailed logs
- **False Positives**: Configure tool exclusions in workflow files
- **Performance Issues**: Adjust workflow triggers or parallelization
- **Secret Issues**: Verify all required secrets are configured

## 📈 Metrics & KPIs

Track these key metrics:

- **Test Coverage**: Target > 80%
- **Security Issues**: Target 0 critical/high severity
- **Code Complexity**: Monitor functions with complexity > 10
- **Performance**: Track benchmark regressions
- **Dependencies**: Keep major versions updated

## 🤝 Contributing

When adding new workflows:

1. Follow the template pattern
2. Include proper error handling
3. Add artifacts for results
4. Update this documentation
5. Test on a feature branch first

## 📚 Resources

- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [CodeQL Documentation](https://codeql.github.com/docs/)
- [Snyk Documentation](https://docs.snyk.io/)
- [SonarQube Documentation](https://docs.sonarqube.org/)
- [Codacy Documentation](https://docs.codacy.com/)

---

*These workflows work together to provide comprehensive code quality assurance and can be easily adapted for other Python projects.*