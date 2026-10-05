from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from app.extensions import login_required
from app.services import (
    change_user_password, get_user_notifications,
    mark_notification_read, mark_all_notifications_read
)

shared_bp = Blueprint('shared', __name__)

@shared_bp.route('/profile')
@login_required
def profile():
    return render_template('shared/profile.html')


@shared_bp.route('/profile/password', methods=['POST'])
@login_required
def change_password():
    current_password = request.form.get('current_password', '')
    new_password = request.form.get('new_password', '')
    confirm_password = request.form.get('confirm_password', '')

    if new_password != confirm_password:
        flash("New passwords do not match.", "danger")
        return redirect(url_for('shared.profile'))

    try:
        change_user_password(session['user']['id'], current_password, new_password)
        flash("Password updated successfully.", "success")
    except Exception as e:
        flash(str(e), "danger")

    return redirect(url_for('shared.profile'))


@shared_bp.route('/notifications')
@login_required
def notifications():
    user_id = session['user']['id']
    items = get_user_notifications(user_id)
    return render_template('shared/notifications.html', notifications=items)


@shared_bp.route('/notifications/<int:id>/read', methods=['POST'])
@login_required
def read_notification(id):
    user_id = session['user']['id']
    mark_notification_read(id, user_id)
    return redirect(url_for('shared.notifications'))


@shared_bp.route('/notifications/read-all', methods=['POST'])
@login_required
def read_all_notifications():
    user_id = session['user']['id']
    mark_all_notifications_read(user_id)
    flash("All notifications marked as read.", "success")
    return redirect(url_for('shared.notifications'))
