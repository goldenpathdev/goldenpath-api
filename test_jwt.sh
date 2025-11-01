#!/bin/bash
# Get a token from the browser console logs (from the user's session)
# For now, just test that the endpoint requires a token

curl -i http://localhost:8000/api/v1/users/me \
  -H "Authorization: Bearer test-token"
