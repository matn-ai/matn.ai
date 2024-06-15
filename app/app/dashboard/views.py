from flask import render_template, redirect, url_for, abort, flash, request,\
    current_app, make_response
from flask_login import login_required, current_user
from flask_sqlalchemy import get_debug_queries
from . import dashboard


@dashboard.route('/dashboard', methods=['GET', 'POST'])
@login_required
def index():

    return render_template('dashboard/dashboard.html')
