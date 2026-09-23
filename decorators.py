import functools
from flask import session, flash, redirect, url_for, request, g
from database import get_db_connection

def login_required(view):
    """Decorator to require login for user/student views."""
    @functools.wraps(view)
    def wrapped_view(**kwargs):
        if g.user is None:
            flash("Please log in to access this page.", "warning")
            return redirect(url_for("auth.login", next=request.path))
        return view(**kwargs)
    return wrapped_view

def admin_required(view):
    """Decorator to require admin role for administrator views."""
    @functools.wraps(view)
    def wrapped_view(**kwargs):
        if g.user is None:
            flash("Please log in with admin credentials.", "warning")
            return redirect(url_for("auth.login", next=request.path))
        if g.user["role"] != "admin":
            flash("Access denied: Administrator privileges required.", "danger")
            return redirect(url_for("student.dashboard"))
        return view(**kwargs)
    return wrapped_view
