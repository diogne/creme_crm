# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2018  Hybird
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

import warnings

from django.http import HttpResponse
from django.shortcuts import get_object_or_404, render

from django.utils.translation import ugettext as _

from creme.creme_core.auth import build_creation_perm as cperm
from creme.creme_core.auth.decorators import login_required, permission_required
from creme.creme_core.utils import get_from_POST_or_404
from creme.creme_core.views import generic

from .. import get_graph_model
from ..constants import DEFAULT_HFILTER_GRAPH
from ..forms.graph import GraphForm, AddRelationTypesForm


Graph = get_graph_model()


def abstract_add_graph(request, form=GraphForm,
                       submit_label=Graph.save_label,
                      ):
    return generic.add_entity(request, form,
                              extra_template_dict={'submit_label': submit_label},
                             )


def abstract_edit_graph(request, graph_id, form=GraphForm):
    return generic.edit_entity(request, graph_id, Graph, form)


def abstract_view_graph(request, graph_id,
                        template='graphs/view_graph.html',
                       ):
    warnings.warn('graphs.views.graph.abstract_view_graph() is deprecated ; '
                  'use the class-based view GraphDetail instead.',
                  DeprecationWarning
                 )
    return generic.view_entity(request, graph_id, Graph, template=template)


@login_required
@permission_required(('graphs', cperm(Graph)))
def add(request):
    return abstract_add_graph(request)


@login_required
@permission_required('graphs')
def dl_png(request, graph_id):
    graph = get_object_or_404(Graph, pk=graph_id)
    user = request.user

    user.has_perm_to_view_or_die(graph)

    try:
        return graph.generate_png(user)
    except Graph.GraphException:
        return render(request, 'graphs/graph_error.html',
                      {'error_message': _(u'This graph is too big!')},
                     )


@login_required
@permission_required('graphs')
def edit(request, graph_id):
    return abstract_edit_graph(request, graph_id)


@login_required
@permission_required('graphs')
def detailview(request, graph_id):
    warnings.warn('graphs.views.graph.detailview() is deprecated.', DeprecationWarning)
    return abstract_view_graph(request, graph_id)


@login_required
@permission_required('graphs')
def listview(request):
    return generic.list_view(request, Graph, hf_pk=DEFAULT_HFILTER_GRAPH)


@login_required
@permission_required('graphs')
def add_relation_types(request, graph_id):
    return generic.add_to_entity(
        request, graph_id, AddRelationTypesForm,
        _('Add relation types to «%s»'),
        entity_class=Graph,
        template='creme_core/generics/blockform/link_popup.html',
    )


@login_required
@permission_required('graphs')
def delete_relation_type(request, graph_id):
    rtype_id = get_from_POST_or_404(request.POST, 'id')
    graph = get_object_or_404(Graph, pk=graph_id)

    request.user.has_perm_to_change_or_die(graph)
    graph.orbital_relation_types.remove(rtype_id)

    return HttpResponse()


# Class-based views  ----------------------------------------------------------


class GraphDetail(generic.detailview.EntityDetail):
    model = Graph
    template_name = 'graphs/view_graph.html'
    pk_url_kwarg = 'graph_id'
