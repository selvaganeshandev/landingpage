# Auth API Curl Requests

## 🔐 **Authentication APIs**

### **1. Login**
```bash
curl -X POST http://localhost:8000/accounts/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@acme.com",
    "password": "admin123"
  }'
```

### **2. Get User Profile**
```bash
curl -X GET http://localhost:8000/accounts/auth/profile/ \
  -H "Authorization: Bearer <access_token>"
```

### **3. Update User Profile**
```bash
curl -X PUT http://localhost:8000/accounts/auth/profile/update/ \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "first_name": "John",
    "last_name": "Smith",
    "email": "john.smith@example.com"
  }'
```

### **4. Logout**
```bash
curl -X POST http://localhost:8000/accounts/auth/logout/ \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "refresh": "<refresh_token>"
  }'
```

## 👥 **Team Management APIs**

### **5. Send Team Invitation (Admin Only)**
```bash
curl -X POST http://localhost:8000/accounts/auth/invite/ \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "newuser@example.com",
    "role": "user",
    "message": "Welcome to our team!"
  }'
```

**Note**: The `organisation` field is automatically set to the logged-in user's organisation.

### **6. Accept Team Invitation**
```bash
curl -X POST http://localhost:8000/accounts/auth/accept-invitation/<invitation_id>/ \
  -H "Content-Type: application/json" \
  -d '{
    "first_name": "John",
    "last_name": "Doe",
    "password": "newpassword123"
  }'
```

## 🔑 **Permission Management APIs**

### **7. Assign Permissions (Admin Only)**
```bash
curl -X POST http://localhost:8000/accounts/auth/permissions/assign/ \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "user": 2,
    "module": "domains",
    "permission_level": "write"
  }'
```

### **8. Check User Permissions**
```bash
# Check all permissions
curl -X GET http://localhost:8000/accounts/auth/permissions/check/ \
  -H "Authorization: Bearer <access_token>"

# Check specific module permission
curl -X GET "http://localhost:8000/accounts/auth/permissions/check/?module=domains" \
  -H "Authorization: Bearer <access_token>"
```

## 🔧 **Standard JWT Endpoints**

### **9. Standard Token Generation**
```bash
curl -X POST http://localhost:8000/accounts/token/ \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@acme.com",
    "password": "admin123"
  }'
```

### **10. Refresh Token**
```bash
curl -X POST http://localhost:8000/accounts/token/refresh/ \
  -H "Content-Type: application/json" \
  -d '{
    "refresh": "<refresh_token>"
  }'
```

## 📝 **Example Complete Flow**

### **Step 1: Login and Get Tokens**
```bash
# Login
curl -X POST http://localhost:8000/accounts/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@acme.com",
    "password": "admin123"
  }'

# Response will include:
# {
#   "access": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
#   "refresh": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
#   "user": {...},
#   "permissions": [...],
#   "message": "Login successful"
# }
```

### **Step 2: Use Access Token for Protected Endpoints**
```bash
# Get profile
curl -X GET http://localhost:8000/accounts/auth/profile/ \
  -H "Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."

# Send invitation (admin only)
curl -X POST http://localhost:8000/accounts/auth/invite/ \
  -H "Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..." \
  -H "Content-Type: application/json" \
  -d '{
    "email": "newuser@example.com",
    "role": "user",
    "message": "Welcome to our team!"
  }'
```

### **Step 3: Refresh Token When Expired**
```bash
# When access token expires, use refresh token
curl -X POST http://localhost:8000/accounts/token/refresh/ \
  -H "Content-Type: application/json" \
  -d '{
    "refresh": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
  }'
```

### **Step 4: Logout**
```bash
# Logout and blacklist refresh token
curl -X POST http://localhost:8000/accounts/auth/logout/ \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "refresh": "<refresh_token>"
  }'
```

## 🎯 **Quick Test Commands**

### **Test Login (Replace with your credentials)**
```bash
curl -X POST http://localhost:8000/accounts/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"email": "root", "password": "admin"}'
```

### **Test Profile (Replace with your access token)**
```bash
curl -X GET http://localhost:8000/accounts/auth/profile/ \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN_HERE"
```

### **Test Permissions (Replace with your access token)**
```bash
curl -X GET http://localhost:8000/accounts/auth/permissions/check/ \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN_HERE"
```

## 📋 **Available Modules for Permissions**

- `dashboard` - Dashboard
- `domains` - Domains
- `keywords` - Keywords
- `prompts` - Prompts
- `analytics` - Analytics
- `reports` - Reports
- `settings` - Settings
- `team` - Team Management

## 🔑 **Permission Levels**

- `read` - Read Only
- `write` - Read & Write
- `admin` - Full Access

## ⚠️ **Important Notes**

1. **Replace `<access_token>`** with the actual JWT access token from login response
2. **Replace `<refresh_token>`** with the actual JWT refresh token from login response
3. **Replace `<invitation_id>`** with the actual UUID from invitation response
4. **Admin-only endpoints**: `/invite/`, `/permissions/assign/` require admin role
5. **All protected endpoints** require `Authorization: Bearer <token>` header
6. **Token expiration**: Access tokens expire in 60 minutes, use refresh token to get new ones
