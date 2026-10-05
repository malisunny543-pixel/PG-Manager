from app.db import query_db, execute_db
from app.services.audit_service import log_audit

# --- Notices ---

def get_notices(property_id=None, role='ALL'):
    """Fetch notices filtered by property and target audience."""
    sql = """
        SELECT n.*, p.name AS property_name, p.code AS property_code,
               u.first_name AS author_first_name, u.last_name AS author_last_name
        FROM notices n
        LEFT JOIN properties p ON p.id = n.property_id
        JOIN users u ON u.id = n.created_by_user_id
        WHERE (n.expires_at IS NULL OR n.expires_at >= CURRENT_TIMESTAMP)
    """
    params = []
    # Property filter: show global notices (property_id IS NULL) + specific property notices
    if property_id is not None:
        sql += " AND (n.property_id IS NULL OR n.property_id = %s)"
        params.append(property_id)

    # Audience filter
    if role == 'TENANT':
        sql += " AND n.target_audience IN ('ALL', 'TENANTS_ONLY')"
    elif role == 'MANAGER':
        sql += " AND n.target_audience IN ('ALL', 'MANAGERS_ONLY')"

    sql += " ORDER BY n.published_at DESC"
    return query_db(sql, tuple(params))


def create_notice(created_by_user_id, title, content, property_id=None, target_audience='ALL', expires_at=None):
    """Publish a new notice announcement."""
    sql = """
        INSERT INTO notices (property_id, target_audience, title, content, expires_at, created_by_user_id)
        VALUES (%s, %s, %s, %s, %s, %s)
    """
    res = execute_db(sql, (
        property_id or None, target_audience, title.strip(),
        content.strip(), expires_at or None, created_by_user_id
    ))
    notice_id = res['lastrowid']
    log_audit('NOTICE_PUBLISHED', 'notices', notice_id, {'title': title, 'audience': target_audience})
    return notice_id


def delete_notice(notice_id, actor_user_id=None):
    """Delete a notice announcement."""
    execute_db("DELETE FROM notices WHERE id = %s", (notice_id,))
    log_audit('NOTICE_DELETED', 'notices', notice_id, actor_id=actor_user_id)


# --- Notifications ---

def get_user_notifications(user_id, limit=30):
    """Get in-app notifications for a user."""
    sql = "SELECT * FROM notifications WHERE user_id = %s ORDER BY created_at DESC LIMIT %s"
    return query_db(sql, (user_id, limit))


def mark_notification_read(notification_id, user_id):
    """Mark a notification as read verifying user ownership."""
    sql = "UPDATE notifications SET is_read = 1 WHERE id = %s AND user_id = %s"
    return execute_db(sql, (notification_id, user_id))


def mark_all_notifications_read(user_id):
    """Mark all unread notifications for a user as read."""
    sql = "UPDATE notifications SET is_read = 1 WHERE user_id = %s AND is_read = 0"
    return execute_db(sql, (user_id,))
