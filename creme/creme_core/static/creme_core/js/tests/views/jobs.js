/* globals QUnitWidgetMixin */

(function($) {

QUnit.module("creme.jobs.js", new QUnitMixin(QUnitAjaxMixin,
                                             QUnitEventMixin,
                                             QUnitWidgetMixin,
                                             QUnitDialogMixin, {
    beforeEach: function() {
        var self = this;
        var backend = this.backend;

        backend.options.enableUriSearch = true;

        this._mockJobsList = [];

        this.setMockBackendGET({
            'mock/jobs': function() {
                return backend.response(200, self.mockJobsList());
            },
            'mock/jobs/invalid': function() {
                return backend.responseJSON(200, {
                    error: 'Invalid job data'
                });
            },
            'mock/jobs/fail': backend.response(400, 'Unable to get jobs')
        });
    },

    setMockJobsList: function(data) {
        this._mockJobsList = data || [];
    },

    jobsListHtml: function(options) {
        options = options || {};
        return (
            '<div><div class="global-error hidden"></div>${jobs}</div>'
        ).template({
            jobs: (options.jobs || []).map(function(item) {
                var progress = item.progress || {};

                return (
                    '<div class="job-status" data-job-id="${id}" data-job-status="${status}" data-job-ack-errors="{ack_errors}">' +
                        '<div class="job-progress">' +
                            '<progress class="job-progress-bar" value="${progressValue}" max="100"></progress>' +
                            '<span class="job-progress-bar-label">${label}</span>' +
                            '${progressLabel}' +
                        '</div>' +
                    '</div>'
                ).template({
                    id: item.id,
                    status: item.status,
                    errors: item.ack_errors,
                    progressValue: progress.percentage,
                    label: progress.label,
                    progressLabel: progress.percentage ? (
                        '<span class="job-progress-percentage-value">${percentage}</span>' +
                        '<span class="job-progress-percentage-mark percentage-mark">%</span>'
                    ).template(progress) : ''
                });
            }).join('\n')
        });
    }
}));

QUnit.test('creme.JobsMonitor (default)', function(assert) {
    var element = $(this.jobsListHtml());
    var controller = new creme.jobs.JobsMonitor('mock/jobs', element);

    deepEqual(element, controller.element());
    equal('mock/jobs', controller.url());
    equal(5000, controller.fetchDelay());
});

QUnit.test('creme.JobsMonitor (properties)', function(assert) {
    var element = $(this.jobsListHtml());
    var controller = new creme.jobs.JobsMonitor('mock/jobs', element);

    deepEqual(element, controller.element());
    equal('mock/jobs', controller.url());
    equal(5000, controller.fetchDelay());

    controller.fetchDelay(0);
    equal(0, controller.fetchDelay());

    controller.onAllJobsFinished(function() {});
    equal(Object.isFunc(controller._onAllJobsFinishedCallBack), true);
});

QUnit.test('creme.JobsMonitor (fetch http error)', function(assert) {
    var element = $(this.jobsListHtml({
        jobs: [
            {id: 'job-a', status: '', ack_errors: '', progress: {percentage: 0, label: 'Job A'}},
            {id: 'job-b', status: '', ack_errors: '', progress: {percentage: 10, label: 'Job B'}}
        ]
    }));
    var controller = new creme.jobs.JobsMonitor('mock/jobs/fail', element);

    controller.fetchDelay(0);
    controller.onAllJobsFinished(this.mockListener('jobs-finished'));

    equal(element.find('.global-error').is('.hidden'), true);
    equal(element.find('.global-error').text(), '');

    controller.fetch();

    deepEqual([
        ['mock/jobs/fail', 'GET', {id: ['job-a', 'job-b']}]
    ], this.mockBackendUrlCalls());

    deepEqual([], this.mockListenerCalls('jobs-finished'));

    equal(element.find('.global-error').is('.hidden'), false);
    equal(element.find('.global-error').text(), 'HTTP server error');
});

QUnit.test('creme.JobsMonitor (fetch invalid data)', function(assert) {
    var element = $(this.jobsListHtml({
        jobs: [
            {id: 'job-a', status: '', ack_errors: '', progress: {percentage: 0, label: 'Job A'}},
            {id: 'job-b', status: '', ack_errors: '', progress: {percentage: 10, label: 'Job B'}}
        ]
    }));
    var controller = new creme.jobs.JobsMonitor('mock/jobs/invalid', element);

    controller.fetchDelay(0);
    controller.onAllJobsFinished(this.mockListener('jobs-finished'));

    equal(element.find('.global-error').is('.hidden'), true);
    equal(element.find('.global-error').text(), '');

    controller.fetch();

    deepEqual([
        ['mock/jobs/invalid', 'GET', {id: ['job-a', 'job-b']}]
    ], this.mockBackendUrlCalls());

    deepEqual([
        []
    ], this.mockListenerCalls('jobs-finished'));

    equal(element.find('.global-error').is('.hidden'), false);
    equal(element.find('.global-error').text(), 'Invalid job data');
});

}(jQuery));
