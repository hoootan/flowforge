#!/bin/bash
# Test the FlowForge Demo Application

BASE_URL="http://localhost:8080"

echo "=== FlowForge Demo Test Script ==="
echo ""

# Check server status
echo "1. Checking server status..."
curl -s "$BASE_URL/" | python3 -m json.tool
echo ""

# Health check
echo "2. Sending health check event..."
curl -s -X POST "$BASE_URL/api/v1/events" \
  -H "Content-Type: application/json" \
  -d '{"name": "system/health", "data": {}}' | python3 -m json.tool
echo ""

# Research agent
echo "3. Testing research agent..."
curl -s -X POST "$BASE_URL/api/v1/events" \
  -H "Content-Type: application/json" \
  -d '{"name": "research/request", "data": {"topic": "AI trends 2024"}}' | python3 -m json.tool
echo ""

# Support ticket
echo "4. Testing support agent..."
curl -s -X POST "$BASE_URL/api/v1/events" \
  -H "Content-Type: application/json" \
  -d '{"name": "support/ticket", "data": {"customer_id": "c_123", "description": "Cannot reset password"}}' | python3 -m json.tool
echo ""

# Multi-agent network
echo "5. Testing multi-agent network..."
curl -s -X POST "$BASE_URL/api/v1/events" \
  -H "Content-Type: application/json" \
  -d '{"name": "support/complex", "data": {"customer_id": "c_123", "description": "Double charged, need refund"}}' | python3 -m json.tool
echo ""

echo "=== All events sent! ==="
