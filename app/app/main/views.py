from flask import render_template, redirect, url_for, abort, flash, request,\
    current_app, make_response
from flask_login import login_required, current_user
from flask_sqlalchemy import get_debug_queries
from . import main
from .forms import EditProfileForm, EditProfileAdminForm, ContentForm
from .. import db
from ..models import Permission, Role, User, Content
from ..decorators import admin_required, permission_required


@main.after_app_request
def after_request(response):
    for query in get_debug_queries():
        if query.duration >= current_app.config['APP_SLOW_DB_QUERY_TIME']:
            current_app.logger.warning(
                'Slow query: %s\nParameters: %s\nDuration: %fs\nContext: %s\n'
                % (query.statement, query.parameters, query.duration,
                   query.context))
    return response


@main.route('/shutdown')
def server_shutdown():
    if not current_app.testing:
        abort(404)
    shutdown = request.environ.get('werkzeug.server.shutdown')
    if not shutdown:
        abort(500)
    shutdown()
    return 'Shutting down...'


@main.route('/', methods=['GET', 'POST'])
def index():
    form = ContentForm()
    if current_user.can(Permission.WRITE) and form.validate_on_submit():
        content = Content(body=form.body.data,
                    author=current_user._get_current_object())
        db.session.add(content)
        db.session.commit()
        return redirect(url_for('.index'))
    page = request.args.get('page', 1, type=int)
    query = Content.query
    pagination = query.order_by(Content.timestamp.desc()).paginate(
        page=page, per_page=current_app.config['APP_POSTS_PER_PAGE'],
        error_out=False)
    contents = pagination.items
    return render_template('index.html', form=form, contents=contents, pagination=pagination)


@main.route('/privacy-policy', methods=['GET'])
def privacy_and_policy_view():
    return render_template('privacy_and_policy.html')

@main.route('/terms-and-conditions', methods=['GET'])
def terms_and_conditions_view():
    return render_template('terms_and_condition.html')


@main.route('/user/<username>')
def user(username):
    user = User.query.filter_by(username=username).first_or_404()
    page = request.args.get('page', 1, type=int)
    pagination = user.contents.order_by(Content.timestamp.desc()).paginate(
        page=page, per_page=current_app.config['APP_POSTS_PER_PAGE'],
        error_out=False)
    contents = pagination.items
    return render_template('user.html', user=user, contents=contents,
                           pagination=pagination)


@main.route('/edit-profile', methods=['GET', 'POST'])
@login_required
def edit_profile():
    form = EditProfileForm()
    if form.validate_on_submit():
        current_user.name = form.name.data
        current_user.location = form.location.data
        current_user.about_me = form.about_me.data
        db.session.add(current_user._get_current_object())
        db.session.commit()
        flash('Your profile has been updated.')
        return redirect(url_for('.user', username=current_user.username))
    form.name.data = current_user.name
    form.location.data = current_user.locationr
    form.about_me.data = current_user.about_me
    return render_template('edit_profile.html', form=form)


@main.route('/edit-profile/<int:id>', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_profile_admin(id):
    user = User.query.get_or_404(id)
    form = EditProfileAdminForm(user=user)
    if form.validate_on_submit():
        user.email = form.email.data
        user.username = form.username.data
        user.confirmed = form.confirmed.data
        user.role = Role.query.get(form.role.data)
        user.name = form.name.data
        user.location = form.location.data
        user.about_me = form.about_me.data
        db.session.add(user)
        db.session.commit()
        flash('The profile has been updated.')
        return redirect(url_for('.user', username=user.username))
    form.email.data = user.email
    form.username.data = user.username
    form.confirmed.data = user.confirmed
    form.role.data = user.role_id
    form.name.data = user.name
    form.location.data = user.location
    form.about_me.data = user.about_me
    return render_template('edit_profile.html', form=form, user=user)


@main.route('/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit(id):
    content = Content.query.get_or_404(id)
    if current_user != content.author and \
            not current_user.can(Permission.ADMIN):
        abort(403)
    form = ContentForm()
    if form.validate_on_submit():
        content.body = form.body.data
        db.session.add(content)
        db.session.commit()
        flash('The content has been updated.')
        return redirect(url_for('.content', id=content.id))
    form.body.data = content.body
    return render_template('edit_content.html', form=form)

