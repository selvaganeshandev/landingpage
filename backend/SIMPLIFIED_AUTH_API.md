# Simplified Authentication API Documentation

## 🔐 **Simplified Auth System**

### **Overview**
A streamlined authentication system with JWT tokens for secure API access. Supports organisation and user login with team management and permission control.

## 🚀 **Authentication APIs**

### **1. Login**
**Endpoint**: `POST /accounts/auth/login/`

**Description**: Login as organisation or user, returns JWT tokens

**Request Body**:
```json
{
    "email": "user@example.com",
    "password": "password123"
}
```

**Response**:
```json
{
    "access": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
    "refresh": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
    "user": {
        "id": 1,
        "email": "user@example.com",
        "first_name": "John",
        "last_name": "Doe",
        "role": "admin",
        "organisation": 1,
        "organisation_name": "Acme Corp"
    },
    "permissions": [
        {
            "id": 1,
            "module": "dashboard",
            "permission_level": "admin",
            "module_display": "Dashboard",
            "permission_display": "Full Access"
        }
    ],
    "message": "Login successful"
}
```

### **2. User Profile**
**Endpoint**: `GET /accounts/auth/profile/`

**Description**: Get current user profile and permissions

**Headers**:
```
Authorization: Bearer <access_token>
```

**Response**:
```json
{
    "user": {
        "id": 1,
        "email": "user@example.com",
        "first_name": "John",
        "last_name": "Doe",
        "role": "admin",
        "organisation": 1,
        "organisation_name": "Acme Corp"
    },
    "permissions": [
        {
            "id": 1,
            "module": "dashboard",
            "permission_level": "admin",
            "module_display": "Dashboard",
            "permission_display": "Full Access"
        }
    ]
}
```

### **3. Update Profile**
**Endpoint**: `PUT /accounts/auth/profile/update/`

**Description**: Update current user profile

**Headers**:
```
Authorization: Bearer <access_token>
```

**Request Body**:
```json
{
    "first_name": "John",
    "last_name": "Smith",
    "email": "john.smith@example.com"
}
```

**Response**:
```json
{
    "message": "Profile updated successfully",
    "user": {
        "id": 1,
        "email": "john.smith@example.com",
        "first_name": "John",
        "last_name": "Smith",
        "role": "admin",
        "organisation": 1,
        "organisation_name": "Acme Corp"
    }
}
```

### **4. Logout**
**Endpoint**: `POST /accounts/auth/logout/`

**Description**: Logout and blacklist refresh token

**Headers**:
```
Authorization: Bearer <access_token>
```

**Request Body**:
```json
{
    "refresh": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
}
```

**Response**:
```json
{
    "message": "Logout successful"
}
```

## 👥 **Team Management APIs**

### **5. Send Invitation**
**Endpoint**: `POST /accounts/auth/invite/`

**Description**: Send team invitation (Organisation admin only)

**Headers**:
```
Authorization: Bearer <access_token>
```

**Request Body**:
```json
{
    "email": "newuser@example.com",
    "role": "user",
    "message": "Welcome to our team!"
}
```

**Response**:
```json
{
    "message": "Invitation sent successfully",
    "invitation": {
        "id": "uuid-string",
        "email": "newuser@example.com",
        "organisation": 1,
        "organisation_name": "Acme Corp",
        "role": "user",
        "status": "pending",
        "expires_at": "2025-10-30T06:48:20Z",
        "is_expired": false,
        "can_be_accepted": true
    }
}
```

### **6. Accept Invitation**
**Endpoint**: `POST /accounts/auth/accept-invitation/{invitation_id}/`

**Description**: Accept team invitation and create user account

**Request Body**:
```json
{
    "first_name": "John",
    "last_name": "Doe",
    "password": "newpassword123"
}
```

**Response**:
```json
{
    "message": "Invitation accepted successfully",
    "user": {
        "id": 2,
        "email": "newuser@example.com",
        "first_name": "John",
        "last_name": "Doe",
        "role": "user",
        "organisation": 1,
        "organisation_name": "Acme Corp"
    }
}
```

## 🔑 **Permission Management APIs**

### **7. Assign Permissions**
**Endpoint**: `POST /accounts/auth/permissions/assign/`

**Description**: Assign permissions to users (Organisation admin only)

**Headers**:
```
Authorization: Bearer <access_token>
```

**Request Body**:
```json
{
    "user": 2,
    "module": "domains",
    "permission_level": "write"
}
```

**Response**:
```json
{
    "message": "Permission assigned successfully",
    "permission": {
        "id": 1,
        "user": 2,
        "user_email": "user@example.com",
        "module": "domains",
        "module_display": "Domains",
        "permission_level": "write",
        "permission_display": "Read & Write",
        "granted_by": 1,
        "granted_by_email": "admin@example.com"
    }
}
```

### **8. Check Permissions**
**Endpoint**: `GET /accounts/auth/permissions/check/`

**Description**: Check user permissions for accessing modules

**Headers**:
```
Authorization: Bearer <access_token>
```

**Query Parameters**:
- `module` (optional): Specific module to check

**Response (All Permissions)**:
```json
{
    "permissions": [
        {
            "id": 1,
            "module": "dashboard",
            "permission_level": "admin",
            "module_display": "Dashboard",
            "permission_display": "Full Access"
        }
    ],
    "user": {
        "id": 1,
        "email": "user@example.com",
        "role": "admin"
    }
}
```

**Response (Specific Module)**:
```json
{
    "module": "domains",
    "permission_level": "write",
    "has_access": true
}
```

## 🔧 **Standard JWT Endpoints**

### **9. Token Obtain Pair**
**Endpoint**: `POST /accounts/token/`

**Description**: Standard JWT token generation

**Request Body**:
```json
{
    "email": "user@example.com",
    "password": "password123"
}
```

**Response**:
```json
{
    "access": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
    "refresh": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
}
```

### **10. Token Refresh**
**Endpoint**: `POST /accounts/token/refresh/`

**Description**: Standard JWT token refresh

**Request Body**:
```json
{
    "refresh": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
}
```

**Response**:
```json
{
    "access": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
}
```

## 📝 **Usage Examples**

### **1. Login**
```bash
curl -X POST http://localhost:8000/accounts/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"email": "root@admin.com", "password": "admin"}'
```

### **2. Get Profile**
```bash
curl -X GET http://localhost:8000/accounts/auth/profile/ \
  -H "Authorization: Bearer <access_token>"
```

### **3. Update Profile**
```bash
curl -X PUT http://localhost:8000/accounts/auth/profile/update/ \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{"first_name": "John", "last_name": "Smith"}'
```

### **4. Send Invitation**
```bash
curl -X POST http://localhost:8000/accounts/auth/invite/ \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{"email": "newuser@example.com", "role": "user", "message": "Welcome!"}'
```

### **5. Accept Invitation**
```bash
curl -X POST http://localhost:8000/accounts/auth/accept-invitation/uuid-here/ \
  -H "Content-Type: application/json" \
  -d '{"first_name": "John", "last_name": "Doe", "password": "password123"}'
```

### **6. Assign Permissions**
```bash
curl -X POST http://localhost:8000/accounts/auth/permissions/assign/ \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{"user": 2, "module": "domains", "permission_level": "write"}'
```

### **7. Check Permissions**
```bash
curl -X GET http://localhost:8000/accounts/auth/permissions/check/ \
  -H "Authorization: Bearer <access_token>"
```

### **8. Logout**
```bash
curl -X POST http://localhost:8000/accounts/auth/logout/ \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{"refresh": "<refresh_token>"}'
```

## 🎯 **Key Features**

- ✅ **JWT Authentication**: Secure token-based authentication
- ✅ **Role-Based Access**: Organisation admin and user roles
- ✅ **Team Management**: Invite and manage team members
- ✅ **Permission System**: Granular module access control
- ✅ **Email Integration**: SMTP invitation system
- ✅ **Profile Management**: Update user profiles
- ✅ **Token Refresh**: Automatic token refresh mechanism
- ✅ **Secure Logout**: Token blacklisting on logout

## 🔄 **Authentication Flow**

1. **Login**: User provides credentials → System returns JWT tokens
2. **API Access**: Client uses access token in Authorization header
3. **Token Expiry**: Access token expires after 60 minutes
4. **Refresh**: Client uses refresh token to get new access token
5. **Logout**: Client sends refresh token to blacklist it

## 🛡️ **Security Features**

- **JWT Tokens**: Cryptographically signed tokens
- **Token Expiration**: Access tokens expire in 60 minutes
- **Refresh Rotation**: Refresh tokens are rotated on use
- **Token Blacklisting**: Refresh tokens are blacklisted after logout
- **Permission Control**: Granular module access permissions
- **Role-Based Access**: Admin and user role separation
