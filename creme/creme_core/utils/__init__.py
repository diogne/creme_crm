# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2011  Hybird
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

from logging import debug

from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ObjectDoesNotExist, PermissionDenied
from django.db.models.query_utils import Q
from django.http import HttpResponse, Http404

from django.core.serializers.json import DjangoJSONEncoder as JSONEncoder

from creme_core.registry import creme_registry


def creme_entity_content_types():
    get_for_model = ContentType.objects.get_for_model
    return (get_for_model(model) for model in creme_registry.iter_entity_models())

def Q_creme_entity_content_types():
    return ContentType.objects.filter(pk__in=[ct_model.pk for ct_model in creme_entity_content_types()])

def get_ct_or_404(ct_id):
    try:
        ct = ContentType.objects.get_for_id(ct_id)
    except ContentType.DoesNotExist:
        raise Http404('No content type with this id: %s' % ct_id)

    return ct

def create_or_update(model, pk=None, **attrs):
    """Get a model instance by its PK, or create a new one ; then set its attributes.
    @param model Django model (class)
    @param pk PK of the wanted instance ; if None, PK is generated by the sql server.
    @param attrs Values of the attributes.
    """
    if pk is not None:
        try:
            instance = model.objects.get(pk=pk)
        except ObjectDoesNotExist:
            instance = model(id=pk)
    else:
        instance = model()

    for key, val in attrs.iteritems():
        setattr(instance, key, val)

    instance.save()

    return instance

def jsonify(func):
    def _aux(*args, **kwargs):
        status = 200

        try:
            rendered = func(*args, **kwargs)
        except Http404, e:
            rendered = unicode(e)
            status = 404
        except PermissionDenied, e:
            rendered = unicode(e)
            status = 403
        except Exception, e:
            debug('Exception in @jsonify(%s): %s', func.__name__, e)
            rendered = unicode(e)
            status = 400

        return HttpResponse(JSONEncoder().encode(rendered), mimetype="text/javascript", status=status)

    return _aux

def get_from_GET_or_404(GET, key): #TODO: factorise with get_from_POST_or_404()
    try:
        return GET[key]
    except KeyError:
        raise Http404('No GET argument with this key: %s' % key)

def get_from_POST_or_404(POST, key, cast=None):
    """@param cast A function that cast the return value, and raise an Exception if it is not possible (eg: int)
    """
    try:
        value = POST[key]

        if cast:
            value = cast(value)
    except KeyError:
        raise Http404('No POST argument with this key: %s' % key)
    except Exception, e:
        raise Http404('Problen with argument "%s" : it can not be coerced (%s)' % (key, str(e)))

    return value

def find_first(iterable, function, *default):
    """
    @param default Optionnal argument.
    """
    for elt in iterable:
        if function(elt):
            return elt

    if default:
        return default[0]

    raise IndexError

def entities2unicode(entities, user):
    """Return a unicdde objects representing a sequence of CremeEntities,
    with care of permissions.
    Tips: for performance, call "CremeEntity.populate_credentials(entities, user)" before.
    """
    return u', '.join(entity.allowed_unicode(user) for entity in entities)

__B2S_MAP = {
        'true':  True,
        'false': False,
    }

def bool_from_str(string):
    b = __B2S_MAP.get(string.lower())

    if b is not None:
        return b

    raise ValueError('Can not be coerced to a boolean value: %s' % str(string))

def truncate_str(str, max_length, suffix=""):
    if max_length <= 0:
        return ""

    len_str = len(str)
    if len_str <= max_length and not suffix:
        return str

    total = max_length - len(suffix)
    if total > 0:
        return str[:total] + suffix
    elif total == 0:
        return suffix
    else:
        return str[:total]
