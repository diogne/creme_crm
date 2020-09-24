/*******************************************************************************
 Creme is a free/open-source Customer Relationship Management software
 Copyright (C) 2020  Hybird

 This program is free software: you can redistribute it and/or modify
 it under the terms of the GNU Affero General Public License as published by
 the Free Software Foundation, either version 3 of the License, or
 (at your option) any later version.

 This program is distributed in the hope that it will be useful,
 but WITHOUT ANY WARRANTY; without even the implied warranty of
 MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 GNU Affero General Public License for more details.

 You should have received a copy of the GNU Affero General Public License
 along with this program.  If not, see <http://www.gnu.org/licenses/>.
 *******************************************************************************/

(function() {
    "use strict";

    function appendStatic(name, method) {
        if (!Math[name]) {
            Math[name] = method;
        }
    };

    appendStatic('absRound', function(value) {
        return (0.5 + value) << 0;
    });

    appendStatic('scaleRound', function(value, precision) {
        var scale = Math.pow(10, precision || 0);
        return Math.round(value * scale) / scale;
    });

    appendStatic('scaleTrunc', function(value, precision) {
        var scale = Math.pow(10, precision || 0);
        return Math.trunc(value * scale) / scale;
    });

    appendStatic('clamp', function(value, min, max) {
        if (!isNaN(max)) {
            value = Math.min(max, value);
        }

        if (!isNaN(min)) {
            value = Math.max(min, value);
        }

        return value;
    });

    appendStatic('sum', function() {
        var result = 0.0;

        for (var i in arguments) {
            var data = arguments[i];

            if (Array.isArray(data)) {
                result += data.reduce(function(item, total) {
                    return item + total;
                }, 0.0);
            } else {
                result += data;
            }
        }

        return result;
    });
}());
