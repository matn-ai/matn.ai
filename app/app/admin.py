from flask_admin import AdminIndexView, expose
from flask_admin.contrib.sqla import ModelView
from flask_login import current_user
from flask import redirect, url_for
from .models import Content, User


class SecureModelView(ModelView):
    column_exclude_list = ['body', 'outlines', 'flow', 'mongo_id', 'user_input', 'password_hash', 'avatar_hash', 'about_me', 'location' ]
    can_view_details = True
    def is_accessible(self):
        return current_user.is_authenticated and current_user.is_administrator()

    def inaccessible_callback(self, name, **kwargs):
        return redirect(url_for('auth.login'))
    


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