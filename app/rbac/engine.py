"""
Role-Based Access Control (RBAC) for Enterprise Memory Infrastructure.
Enforces role-based permissions for all operations.
"""

from dataclasses import dataclass
from typing import List, Optional
from datetime import datetime
from app.database import db


class PermissionDenied(Exception):
    """Raised when user lacks required permission."""
    pass


@dataclass
class Role:
    """Role definition with permissions."""
    id: str
    tenant_id: str
    role_name: str
    description: Optional[str]
    can_ingest: bool
    can_retrieve: bool
    can_delete: bool
    can_admin: bool
    max_scope: str
    is_system_role: bool


@dataclass
class UserPermissions:
    """Aggregated permissions for a user."""
    tenant_id: str
    user_id: str
    roles: List[Role]
    can_ingest: bool
    can_retrieve: bool
    can_delete: bool
    can_admin: bool
    max_scope: str


class RBACEngine:
    """
    Role-Based Access Control engine.
    
    Responsibilities:
    - Verify user permissions
    - Manage roles and assignments
    - Enforce scope-based access
    """
    
    def __init__(self):
        self._permissions_cache = {}
    
    def get_user_permissions(self, tenant_id: str, user_id: str) -> UserPermissions:
        """
        Get aggregated permissions for user.
        
        Args:
            tenant_id: Tenant identifier
            user_id: User identifier
            
        Returns:
            UserPermissions object
            
        Raises:
            PermissionDenied: If user has no roles
        """
        cache_key = f"{tenant_id}:{user_id}"
        
        # Check cache
        if cache_key in self._permissions_cache:
            return self._permissions_cache[cache_key]
        
        # Fetch from database
        with db.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT 
                        r.id,
                        r.tenant_id,
                        r.role_name,
                        r.description,
                        r.can_ingest,
                        r.can_retrieve,
                        r.can_delete,
                        r.can_admin,
                        r.max_scope,
                        r.is_system_role
                    FROM user_roles ur
                    JOIN roles r ON ur.role_id = r.id
                    WHERE ur.tenant_id = %s
                      AND ur.user_id = %s
                      AND (ur.expires_at IS NULL OR ur.expires_at > CURRENT_TIMESTAMP)
                """, (tenant_id, user_id))
                
                rows = cur.fetchall()
                
                if not rows:
                    # Assign default 'user' role if no roles assigned
                    return self._assign_default_role(tenant_id, user_id)
                
                roles = [
                    Role(
                        id=row[0],
                        tenant_id=row[1],
                        role_name=row[2],
                        description=row[3],
                        can_ingest=row[4],
                        can_retrieve=row[5],
                        can_delete=row[6],
                        can_admin=row[7],
                        max_scope=row[8],
                        is_system_role=row[9]
                    )
                    for row in rows
                ]
                
                # Aggregate permissions (OR logic - any role grants permission)
                permissions = UserPermissions(
                    tenant_id=tenant_id,
                    user_id=user_id,
                    roles=roles,
                    can_ingest=any(r.can_ingest for r in roles),
                    can_retrieve=any(r.can_retrieve for r in roles),
                    can_delete=any(r.can_delete for r in roles),
                    can_admin=any(r.can_admin for r in roles),
                    max_scope=self._get_max_scope(roles)
                )
                
                # Cache permissions
                self._permissions_cache[cache_key] = permissions
                return permissions
    
    def _assign_default_role(self, tenant_id: str, user_id: str) -> UserPermissions:
        """Assign default 'user' role to new user."""
        with db.get_connection() as conn:
            with conn.cursor() as cur:
                # Get 'user' role for tenant
                cur.execute("""
                    SELECT id FROM roles
                    WHERE tenant_id = %s AND role_name = 'user'
                """, (tenant_id,))
                
                role_row = cur.fetchone()
                
                if role_row:
                    # Assign role
                    cur.execute("""
                        INSERT INTO user_roles (tenant_id, user_id, role_id, assigned_by)
                        VALUES (%s, %s, %s, 'system')
                        ON CONFLICT DO NOTHING
                    """, (tenant_id, user_id, role_row[0]))
                    conn.commit()
                
                # Return default permissions
                return UserPermissions(
                    tenant_id=tenant_id,
                    user_id=user_id,
                    roles=[],
                    can_ingest=True,
                    can_retrieve=True,
                    can_delete=False,
                    can_admin=False,
                    max_scope='team'
                )
    
    def _get_max_scope(self, roles: List[Role]) -> str:
        """
        Get maximum scope from roles.
        
        Scope hierarchy: user < team < organization < global
        """
        scope_hierarchy = ['user', 'team', 'organization', 'global']
        max_scope_idx = 0
        
        for role in roles:
            try:
                idx = scope_hierarchy.index(role.max_scope)
                max_scope_idx = max(max_scope_idx, idx)
            except ValueError:
                continue
        
        return scope_hierarchy[max_scope_idx]
    
    def verify_permission(
        self,
        tenant_id: str,
        user_id: str,
        required_permission: str
    ) -> None:
        """
        Verify user has required permission.
        
        Args:
            tenant_id: Tenant identifier
            user_id: User identifier
            required_permission: 'ingest', 'retrieve', 'delete', or 'admin'
            
        Raises:
            PermissionDenied: If user lacks permission
        """
        permissions = self.get_user_permissions(tenant_id, user_id)
        
        permission_map = {
            'ingest': permissions.can_ingest,
            'retrieve': permissions.can_retrieve,
            'delete': permissions.can_delete,
            'admin': permissions.can_admin
        }
        
        if required_permission not in permission_map:
            raise ValueError(f"Unknown permission: {required_permission}")
        
        if not permission_map[required_permission]:
            roles_str = ', '.join(r.role_name for r in permissions.roles)
            raise PermissionDenied(
                f"User '{user_id}' with roles [{roles_str}] lacks '{required_permission}' permission"
            )
    
    def verify_scope_access(
        self,
        tenant_id: str,
        user_id: str,
        requested_scope: str
    ) -> None:
        """
        Verify user can access requested scope.
        
        Args:
            tenant_id: Tenant identifier
            user_id: User identifier
            requested_scope: Scope to access
            
        Raises:
            PermissionDenied: If user cannot access scope
        """
        permissions = self.get_user_permissions(tenant_id, user_id)
        
        scope_hierarchy = ['user', 'team', 'organization', 'global']
        
        try:
            max_scope_idx = scope_hierarchy.index(permissions.max_scope)
            requested_scope_idx = scope_hierarchy.index(requested_scope)
        except ValueError:
            raise ValueError(f"Invalid scope: {requested_scope}")
        
        if requested_scope_idx > max_scope_idx:
            raise PermissionDenied(
                f"User '{user_id}' cannot access '{requested_scope}' scope. "
                f"Maximum allowed: '{permissions.max_scope}'"
            )
    
    def create_role(
        self,
        tenant_id: str,
        role_name: str,
        description: str,
        can_ingest: bool,
        can_retrieve: bool,
        can_delete: bool,
        can_admin: bool,
        max_scope: str = 'user'
    ) -> str:
        """
        Create new role.
        
        Args:
            tenant_id: Tenant identifier
            role_name: Role name
            description: Role description
            can_ingest: Ingest permission
            can_retrieve: Retrieve permission
            can_delete: Delete permission
            can_admin: Admin permission
            max_scope: Maximum scope
            
        Returns:
            Role ID
        """
        with db.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO roles (
                        tenant_id,
                        role_name,
                        description,
                        can_ingest,
                        can_retrieve,
                        can_delete,
                        can_admin,
                        max_scope
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING id
                """, (
                    tenant_id,
                    role_name,
                    description,
                    can_ingest,
                    can_retrieve,
                    can_delete,
                    can_admin,
                    max_scope
                ))
                
                role_id = cur.fetchone()[0]
                conn.commit()
                return str(role_id)
    
    def assign_role(
        self,
        tenant_id: str,
        user_id: str,
        role_id: str,
        assigned_by: str,
        expires_at: Optional[datetime] = None
    ) -> None:
        """
        Assign role to user.
        
        Args:
            tenant_id: Tenant identifier
            user_id: User identifier
            role_id: Role identifier
            assigned_by: Who assigned the role
            expires_at: Optional expiration
        """
        with db.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO user_roles (
                        tenant_id,
                        user_id,
                        role_id,
                        assigned_by,
                        expires_at
                    ) VALUES (%s, %s, %s, %s, %s)
                    ON CONFLICT (tenant_id, user_id, role_id) DO NOTHING
                """, (tenant_id, user_id, role_id, assigned_by, expires_at))
                
                conn.commit()
        
        # Invalidate cache
        self.invalidate_cache(tenant_id, user_id)
    
    def revoke_role(
        self,
        tenant_id: str,
        user_id: str,
        role_id: str
    ) -> None:
        """
        Revoke role from user.
        
        Args:
            tenant_id: Tenant identifier
            user_id: User identifier
            role_id: Role identifier
        """
        with db.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    DELETE FROM user_roles
                    WHERE tenant_id = %s
                      AND user_id = %s
                      AND role_id = %s
                """, (tenant_id, user_id, role_id))
                
                conn.commit()
        
        # Invalidate cache
        self.invalidate_cache(tenant_id, user_id)
    
    def invalidate_cache(self, tenant_id: str, user_id: str) -> None:
        """
        Invalidate cached permissions.
        
        Args:
            tenant_id: Tenant identifier
            user_id: User identifier
        """
        cache_key = f"{tenant_id}:{user_id}"
        if cache_key in self._permissions_cache:
            del self._permissions_cache[cache_key]


# Global RBAC engine instance
rbac_engine = RBACEngine()
