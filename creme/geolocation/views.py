# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2014-2020  Hybird
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

# from itertools import chain
from functools import partial

from django.db.transaction import atomic
# from django.contrib.contenttypes.models import ContentType
from django.http import HttpResponse
from django.shortcuts import get_object_or_404

# from creme.persons import get_contact_model, get_organisation_model, get_address_model
from creme import persons
from creme.creme_core.http import CremeJsonResponse
# from creme.creme_core.auth.decorators import permission_required, login_required
from creme.creme_core.models import EntityFilter
from creme.creme_core.utils import get_from_GET_or_404, get_from_POST_or_404
# from creme.creme_core.views.decorators import jsonify, POST_only
from creme.creme_core.views.generic import CheckedView

from .models import GeoAddress
from .utils import address_as_dict, addresses_from_persons, get_radius

Address = persons.get_address_model()


# @login_required
# @permission_required('persons')
# @POST_only
# @atomic
# def set_address_info(request):
#     get = partial(get_from_POST_or_404, request.POST)
#     address = get_object_or_404(
#         get_address_model().objects.select_for_update(),
#         id=get('id', cast=int),
#     )
#
#     request.user.has_perm_to_change_or_die(address.owner)
#
#     data = {'latitude':  get('latitude'),
#             'longitude': get('longitude'),
#             'geocoded':  get('geocoded').lower() == 'true',
#             'status':    get('status'),
#            }
#
#     try:
#         address.geoaddress.update(**data)
#     except GeoAddress.DoesNotExist:
#         GeoAddress.objects.create(address=address, **data)
#
#     return HttpResponse()
class AddressInfoSetting(CheckedView):
    permissions = 'persons'

    @atomic
    def post(self, request, *args, **kwargs):
        get_arg = partial(get_from_POST_or_404, request.POST)
        address = get_object_or_404(
            Address.objects.select_for_update(),
            id=get_arg('id', cast=int),
        )

        request.user.has_perm_to_change_or_die(address.owner)

        data = {
            'latitude': get_arg('latitude'),
            'longitude': get_arg('longitude'),
            # TODO: utils.bool_from_str_extended()
            'geocoded': get_arg('geocoded').lower() == 'true',
            'status': get_arg('status'),
        }

        try:
            address.geoaddress.update(**data)
        except GeoAddress.DoesNotExist:
            GeoAddress.objects.create(address=address, **data)

        return HttpResponse()


# @login_required
# @permission_required('persons')
# @jsonify
# def get_addresses_from_filter(request):
#     filter_id = request.GET.get('id')
#     entity_filter = get_object_or_404(EntityFilter, pk=filter_id) if filter_id else None
#     owner_groups = (get_contact_model().objects, get_organisation_model().objects)
#
#     user = request.user
#
#     if entity_filter:
#         model = entity_filter.entity_type.model_class()
#         owner_groups = (entity_filter.filter(model.objects, user),)
#
#     addresses = list(chain(*(iter(addresses_from_persons(owners, user))
#         for owners in owner_groups)))
#
#     GeoAddress.populate_geoaddresses(addresses)
#
#     return {'addresses': [address_as_dict(address) for address in addresses]}
class BaseAddressesInformation(CheckedView):
    permissions = 'persons'
    response_class = CremeJsonResponse
    efilter_id_arg = 'id'

    def get_efilter_id(self):
        return self.request.GET.get(self.efilter_id_arg)

    def get_efilter(self):
        filter_id = self.get_efilter_id()
        return get_object_or_404(EntityFilter, pk=filter_id) if filter_id else None

    def get_info(self, request):
        raise NotImplementedError()

    def get(self, request, *args, **kwargs):
        return self.response_class(self.get_info(request))


class AddressesInformation(BaseAddressesInformation):
    entity_classes = [
        persons.get_contact_model(),
        persons.get_organisation_model(),
    ]

    def get_info(self, request):
        entity_filter = self.get_efilter()
        user = request.user

        def owner_groups():
            if entity_filter:
                # TODO: assert in self.entity_classes
                model = entity_filter.entity_type.model_class()
                yield entity_filter.filter(model.objects.all(), user=user)
            else:
                for model in self.entity_classes:
                    yield model.objects.all()

        addresses = [
            address
            for owners in owner_groups()
            for address in addresses_from_persons(owners, user)
        ]

        GeoAddress.populate_geoaddresses(addresses)

        return {'addresses': [address_as_dict(address) for address in addresses]}


# @login_required
# @permission_required('persons')
# @jsonify
# def get_neighbours(request):
#     GET = request.GET
#     address_id = get_from_GET_or_404(GET, 'address_id', int)
#     filter_id = get_from_GET_or_404(GET, 'filter_id', default=None)
#
#     source = get_object_or_404(get_address_model(), id=address_id)
#     distance = get_radius()
#     entity_filter = get_object_or_404(EntityFilter, id=filter_id) if filter_id else None
#
#     query_distance = GET.get('distance', '')
#
#     if query_distance.isdigit():
#         distance = float(query_distance)
#
#     neighbours = source.geoaddress.neighbours(distance).select_related('address')
#
#     if entity_filter:
#         model = entity_filter.entity_type.model_class()
#
#         # filter owners of neighbours
#         owner_ids = entity_filter.filter(
#             model.objects.filter(
#                 is_deleted=False,
#                 pk__in=neighbours.values_list('address__object_id', flat=True),
#             )
#         ).values_list('pk', flat=True)
#         neighbours = neighbours.filter(
#             address__content_type=ContentType.objects.get_for_model(model),
#             address__object_id__in=owner_ids,
#         )
#
#     # Filter credentials
#     has_perm = request.user.has_perm_to_view
#     addresses = [address_as_dict(neighbor.address)
#                     for neighbor in neighbours if has_perm(neighbor.address.owner)
#                 ]
#
#     return {'source_address': address_as_dict(source),
#             'addresses': addresses,
#            }
class NeighboursInformation(BaseAddressesInformation):
    efilter_id_arg = 'filter_id'

    def get_info(self, request):
        GET = request.GET
        source = get_object_or_404(
            Address,
            id=get_from_GET_or_404(GET, 'address_id', int),
        )
        entity_filter = self.get_efilter()

        # TODO: error if value but invalid as float...
        query_distance = GET.get('distance', '')
        distance = float(query_distance) if query_distance.isdigit() else get_radius()

        neighbours = source.geoaddress.neighbours(distance).select_related('address')

        if entity_filter:
            ctype = entity_filter.entity_type

            # Filter owners of neighbours
            owner_ids = entity_filter.filter(
                ctype.model_class().objects.filter(
                    is_deleted=False,
                    pk__in=neighbours.values_list('address__object_id', flat=True),
                )
            ).values_list('pk', flat=True)
            neighbours = neighbours.filter(
                address__content_type=ctype,
                address__object_id__in=owner_ids,
            )

        # Filter credentials
        has_perm = request.user.has_perm_to_view
        addresses = [
            address_as_dict(neighbour.address)
            for neighbour in neighbours
            if has_perm(neighbour.address.owner)  # TODO: populate owner ?
        ]

        return {
            'source_address': address_as_dict(source),
            'addresses': addresses,
        }
