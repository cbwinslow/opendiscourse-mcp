#!/bin/bash
# API Key Update Helper Script

echo "🔑 OpenDiscourse API Key Management"
echo ""

# Show current keys (masked)
echo "Current API Keys:"
if [ -f "mcp_server/.env" ]; then
    grep "API_KEY" mcp_server/.env | sed 's/=.*/=***masked***/'
else
    echo "❌ .env file not found"
    exit 1
fi

echo ""
echo "Which API key would you like to update?"
echo "1) Congress API Key"
echo "2) GovInfo API Key"
echo "3) Test all keys"
echo "4) Exit"
echo ""

read -p "Enter choice (1-4): " choice

case $choice in
    1)
        echo "Enter new Congress API Key:"
        read -s congress_key
        sed -i "s/CONGRESS_API_KEY=.*/CONGRESS_API_KEY=\"$congress_key\"/" mcp_server/.env
        echo "✅ Congress API key updated"
        ;;
    2)
        echo "Enter new GovInfo API Key:"
        read -s govinfo_key
        sed -i "s/GOVINFO_API_KEY=.*/GOVINFO_API_KEY=\"$govinfo_key\"/" mcp_server/.env
        echo "✅ GovInfo API key updated"
        ;;
    3)
        echo "Testing API keys..."
        export $(cat mcp_server/.env | xargs)

        # Test Congress API
        congress_status=$(python -c "
import requests
try:
    response = requests.get('https://api.congress.gov/bill', params={'page': 1, 'congress': 118, 'api_key': '$CONGRESS_API_KEY'}, timeout=10)
    print(response.status_code)
except:
    print('ERROR')
        " 2>/dev/null)

        # Test GovInfo API
        govinfo_status=$(python -c "
import requests
try:
    response = requests.get('https://api.govinfo.gov/collections', params={'api_key': '$GOVINFO_API_KEY'}, timeout=10)
    print(response.status_code)
except:
    print('ERROR')
        " 2>/dev/null)

        echo "API Key Test Results:"
        if [ "$congress_status" = "200" ]; then
            echo "✅ Congress API: Valid"
        else
            echo "❌ Congress API: Invalid (Status: $congress_status)"
        fi

        if [ "$govinfo_status" = "200" ]; then
            echo "✅ GovInfo API: Valid"
        else
            echo "❌ GovInfo API: Invalid (Status: $govinfo_status)"
        fi
        ;;
    4)
        echo "Exiting..."
        exit 0
        ;;
    *)
        echo "Invalid choice"
        exit 1
        ;;
esac

echo ""
echo "Remember to restart any running ingestion processes after key updates."