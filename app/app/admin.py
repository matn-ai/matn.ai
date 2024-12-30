from flask_admin import AdminIndexView, expose
from flask_admin.contrib.sqla import ModelView
from flask_login import current_user
from flask import redirect, url_for, flash
from .models import Content, User, Contact
from datetime import datetime
import pytz

class SecureModelView(ModelView):
    column_exclude_list = ['body', 'outlines', 'flow', 'mongo_id', 'user_input', 'password_hash', 'avatar_hash', 'about_me', 'location' ]
    can_view_details = True
    def is_accessible(self):
        return current_user.is_authenticated and current_user.is_administrator()

    def inaccessible_callback(self, name, **kwargs):
        return redirect(url_for('auth.login'))
    


class ContactModelView(SecureModelView):
    # Customize the list view
    column_list = ['name', 'organization', 'email', 'phone', 'created_at', 'is_read']
    column_searchable_list = ['name', 'email', 'phone', 'organization']
    column_filters = ['created_at', 'is_read']
    column_default_sort = ('created_at', True)  # Sort by created_at descending
    
    # Customize the form view
    form_excluded_columns = ['created_at']
    
    # Customize labels
    column_labels = {
        'name': 'نام',
        'organization': 'سازمان',
        'email': 'ایمیل',
        'phone': 'تلفن',
        'message': 'پیام',
        'created_at': 'تاریخ ایجاد',
        'is_read': 'خوانده شده'
    }
    
    # Custom formatters
    column_formatters = {
        'created_at': lambda v, c, m, p: m.created_at.strftime('%Y-%m-%d %H:%M:%S'),
        'is_read': lambda v, c, m, p: 'بله' if m.is_read else 'خیر'
    }
    
    def on_model_change(self, form, model, is_created):
        """Update timestamps on model change"""
        if is_created:
            model.created_at = datetime.now(pytz.timezone('Asia/Tehran'))

    def after_model_change(self, form, model, is_created):
        """Flash message after model is changed"""
        if is_created:
            flash(f'پیام جدید از {model.name} دریافت شد', 'success')
        else:
            flash(f'پیام از {model.name} بروزرسانی شد', 'info')


class SecureAdminIndexView(AdminIndexView):
    @expose('/')
    def index(self):
        if not current_user.is_authenticated or not current_user.is_administrator():
            return redirect(url_for('auth.login'))
        return super(SecureAdminIndexView, self).index()
    
    
def load_admin_views():
    from . import db, admin 
    admin.add_view(SecureModelView(Content, db.session))
    admin.add_view(SecureModelView(User, db.session))
    admin.add_view(ContactModelView(Contact, db.session))
