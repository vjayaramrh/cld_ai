# API Verification Template

**Use this template BEFORE coding a new module** to verify the endpoint contract.

## Module: [module_name]

### Endpoint Information

**API Path:** `/v2/...`  
**HTTP Method:** GET / POST / PATCH / DELETE  
**Pattern:** info / state / action  
**Issue:** #...

---

### Step 1: Query the Spec

```bash
# Query command (customize for your endpoint)
curl -s "https://api.openshift.com/api/assisted-install/v2/openapi" | \
  jq '.paths."/v2/your-endpoint".get.parameters'
```

**Spec Output:**
```json
[paste the jq output here]
```

---

### Step 2: Extract Requirements

**Path parameters:**
- [ ] `param_name` (type, required/optional)

**Query parameters:**
- [ ] `param_name` (type, required/optional, choices: [...])

**Body parameters (for POST/PATCH):**
```bash
# First, inspect the operation's body parameter to get the schema reference
curl -s "https://api.openshift.com/api/assisted-install/v2/openapi" | \
  jq '.paths."/v2/your-endpoint".post.parameters[] | select(.in == "body") | .schema'

# Then resolve the $ref (e.g., "#/definitions/infra-env-create-params")
curl -s "https://api.openshift.com/api/assisted-install/v2/openapi" | \
  jq '.definitions."infra-env-create-params" | {required, properties: .properties | keys}'
```

**Required body fields:**
- [ ] `field_name` (type)

**Optional body fields:**
- [ ] `field_name` (type, default: ...)

---

### Step 3: Response Shape

```bash
# Check response schema for your HTTP method and success code
# GET typically returns 200, POST returns 201, DELETE may return 204 (no content)

# For GET 200
curl -s "https://api.openshift.com/api/assisted-install/v2/openapi" | \
  jq '.paths."/v2/your-endpoint".get.responses."200".schema'

# For POST 201
curl -s "https://api.openshift.com/api/assisted-install/v2/openapi" | \
  jq '.paths."/v2/your-endpoint".post.responses."201".schema'

# Check all 2xx responses to see which codes the endpoint returns
curl -s "https://api.openshift.com/api/assisted-install/v2/openapi" | \
  jq '.paths."/v2/your-endpoint".METHOD.responses | keys'
```

**Response structure:**
```text
[describe what the API returns]
```

---

### Step 4: Module Parameter Mapping

| API Parameter | Module Parameter | Type | Required | Notes |
|---------------|------------------|------|----------|-------|
| `api_param` | `module_param` | str | yes | ... |

**Additional module parameters (not from API):**
- `api_token` (str, secret, fallback from env)
- `offline_token` (str, secret, fallback from env)
- `timeout` (int, default: 30) - client-side HTTP timeout
- `base_url` (str, optional) - for testing with mock server

---

### Step 5: Verification Checklist

- [ ] All required API parameters are required in module
- [ ] All API parameter types match module types
- [ ] API enums/choices are enforced in module
- [ ] EXAMPLES use only real API parameters
- [ ] RETURN block matches actual API response shape
- [ ] No parameters assumed without checking spec

---

## Example: openshift_version_info

**Endpoint:** `/v2/openshift-versions` (GET)

**Spec parameters:**
```json
[
  {
    "name": "version",
    "type": "string",
    "in": "query",
    "required": false
  },
  {
    "name": "only_latest",
    "type": "boolean",
    "in": "query",
    "required": false
  }
]
```

**Module parameters:**
- `version` (str, optional) ✅ matches spec
- `only_latest` (bool, optional, default: false) ✅ matches spec
- `api_token` (str, secret) - client param
- `offline_token` (str, secret) - client param
- `timeout` (int, default: 30) - client param

**Verification:** ✅ All API parameters accounted for, types match
