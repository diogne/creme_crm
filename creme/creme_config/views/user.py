# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2013  Hybird
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
################################################################################

from django.utils.translation import ugettext as _
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, render
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.auth.models import User

from creme.creme_core.views.generic import add_model_with_popup, edit_model_with_popup
from creme.creme_core.auth.decorators import superuser_required

from ..forms.user import (UserAddForm, UserChangePwForm, UserEditForm,
                          TeamCreateForm, TeamEditForm, UserAssignationForm)


@login_required
@superuser_required
def change_password(request, user_id):
    return edit_model_with_popup(request, {'pk': user_id}, User,
                                 UserChangePwForm, _(u'Change password for <%s>')
                                )

@login_required
@superuser_required
def add(request):
    return add_model_with_popup(request, UserAddForm, _(u'New user'))

@login_required
@superuser_required
def add_team(request):
    return add_model_with_popup(request, TeamCreateForm, _(u'New team'))

@login_required
@permission_required('creme_config')
def portal(request):
    return render(request, 'creme_config/user_portal.html')

@login_required
@superuser_required
def edit(request, user_id):
    return edit_model_with_popup(request, {'pk': user_id, 'is_team': False}, User, UserEditForm)

@login_required
@superuser_required
def edit_team(request, user_id):
    return edit_model_with_popup(request, {'pk': user_id, 'is_team': True}, User, TeamEditForm)

@login_required
@superuser_required
def delete(request, user_id):
    """Delete a User (who can be a Team). Objects linked to this User are
    linked to a new User.
    """

    if int(user_id) == request.user.id:
        return HttpResponse(_(u"You can't delete the last super user."), status=400)

    user_to_delete = get_object_or_404(User, pk=user_id)

#    if not user_to_delete.is_team and User.objects.filter(is_superuser=True).count() == 1:
#        return HttpResponse(_(u"You can't delete the last super user."), status=400)

    try:
        return add_model_with_popup(request, UserAssignationForm,
                                    _(u'Delete %s and assign his files to user') % user_to_delete,
                                    initial={'user_to_delete': user_to_delete},
                                   )
    except Exception:
        return HttpResponse(_(u"You can't delete this user."), status=400)
