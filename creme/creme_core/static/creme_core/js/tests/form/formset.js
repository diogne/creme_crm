/* global QUnitFormMixin */
(function($) {

QUnit.module("creme.form.Form", new QUnitMixin(QUnitEventMixin,
                                               QUnitAjaxMixin,
                                               QUnitFormMixin, {
    beforeEach: function() {
        var backend = this.backend;
        this.setMockBackendGET({
            'mock/submit': backend.response(200, ''),
            'mock/other': backend.response(200, '')
        });

        this.setMockBackendPOST({
            'mock/submit': backend.response(200, ''),
            'mock/other': backend.response(200, '')
        });
    }
}));

QUnit.test('creme.form.FormSet (empty, defaults)', function() {
    var element = $('<div></div>');
    var formset = new creme.form.FormSet(element);

    equal(true, formset.isValid());
    equal(true, formset.isValidHtml());

    deepEqual([], formset.forms());
    deepEqual({}, formset.initialData());
    deepEqual({}, formset.data());
    deepEqual({
        prefix: '',
        cleanedData: {
            total: 0,
            initial: 0,
            max: 0
        },
        data: {},
        errors: [],
        fieldErrors: {},
        isValid: true
    }, formset.clean());
    deepEqual({
        total: 0,
        initial: 0,
        max: 0
    }, formset.stateData());

    this.equalOuterHtml(element, formset.element());
});

}(jQuery));
