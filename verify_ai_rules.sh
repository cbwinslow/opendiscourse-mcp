#!/bin/bash
# AI Rules Verification Script
# Tests that AI agent rules are properly enforced

echo "🤖 AI Agent Rules Verification"
echo "================================"

# Test 1: Check if rules file exists
echo "📋 Test 1: Rules file existence"
if [[ -f ~/.ai_agent_rules ]]; then
    echo "✅ AI rules file exists"
else
    echo "❌ AI rules file missing"
    exit 1
fi

# Test 2: Check if rules are sourced in .zshrc
echo ""
echo "📋 Test 2: Rules integration in .zshrc"
if grep -q "ai_agent_rules" ~/.zshrc; then
    echo "✅ Rules are sourced in .zshrc"
else
    echo "❌ Rules not integrated in .zshrc"
    exit 1
fi

# Test 3: Check if AI_RULES_ACTIVE environment variable is set
echo ""
echo "📋 Test 3: Environment variable activation"
if [[ "$AI_RULES_ACTIVE" == "true" ]]; then
    echo "✅ AI rules environment active"
else
    echo "⚠️  AI rules environment not active (restart shell to activate)"
fi

# Test 4: Verify key rule functions are available
echo ""
echo "📋 Test 4: Rule functions availability"
if declare -f ai_show_rules >/dev/null; then
    echo "✅ ai_show_rules function available"
else
    echo "❌ ai_show_rules function missing"
    exit 1
fi

if declare -f ai_verify_compliance >/dev/null; then
    echo "✅ ai_verify_compliance function available"
else
    echo "❌ ai_verify_compliance function missing"
    exit 1
fi

# Test 5: Run compliance verification
echo ""
echo "📋 Test 5: Running compliance verification"
if ai_verify_compliance; then
    echo "✅ Compliance verification passed"
else
    echo "❌ Compliance verification failed"
    exit 1
fi

echo ""
echo "🎉 All AI Agent Rules verification tests passed!"
echo ""
echo "📖 To view rules: ai_show_rules"
echo "🔍 To verify compliance: ai_verify_compliance"
echo "⚠️  Rules are enforced for all AI agents in this environment"