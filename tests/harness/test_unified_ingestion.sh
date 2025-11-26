#!/bin/bash
# Quick test script for unified ingestion

echo "🧪 Testing Unified Ingestion Script"
echo "===================================="

# Test 1: Help (should work)
echo "📋 Testing help output..."
python unified_ingestion.py --help > /dev/null
if [ $? -eq 0 ]; then
    echo "✅ Help command works"
else
    echo "❌ Help command failed"
    exit 1
fi

# Test 2: Dry run with Congress (should work without API keys for dry run)
echo ""
echo "🏛️ Testing Congress dry run..."
python unified_ingestion.py \
    --source congress \
    --data-type bills \
    --congress 118 \
    --dry-run \
    --max-pages 1 \
    --disable-async

if [ $? -eq 0 ]; then
    echo "✅ Congress dry run works"
else
    echo "❌ Congress dry run failed"
fi

# Test 3: Comprehensive dry run
echo ""
echo "🌐 Testing comprehensive dry run..."
python unified_ingestion.py \
    --source all \
    --comprehensive \
    --dry-run \
    --max-pages 1 \
    --disable-async

if [ $? -eq 0 ]; then
    echo "✅ Comprehensive dry run works"
else
    echo "❌ Comprehensive dry run failed"
fi

echo ""
echo "🎉 Basic tests completed!"
echo ""
echo "📖 Usage Examples:"
echo "  # Real Congress ingestion:"
echo "  python unified_ingestion.py --source congress --data-type bills --congress 118"
echo ""
echo "  # All Congress data types:"
echo "  python unified_ingestion.py --source congress --data-type all --congress 118"
echo ""
echo "  # Multiple Congresses:"
echo "  python unified_ingestion.py --source congress --data-type bills --congress 116 117 118"
echo ""
echo "  # GovInfo collection:"
echo "  python unified_ingestion.py --source govinfo --collection BILLS --year 2023"
echo ""
echo "  # OpenStates jurisdiction:"
echo "  python unified_ingestion.py --source openstates --jurisdiction nc"
echo ""
echo "  # Everything:"
echo "  python unified_ingestion.py --source all --comprehensive"