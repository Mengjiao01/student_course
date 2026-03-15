// Shared static entry point for template scripts.

// Escape API data before injecting it into modal markup.
function escapeHtml(value) {
    return String(value)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#39;");
}

// Load teacher and student details into the shared admin modal on demand.
function initAdminCourseDetailModal() {
    if (!document.body.classList.contains("page-admin-course-detail")) {
        return;
    }

    const modalElement = document.getElementById("detailModal");
    if (!modalElement || !window.bootstrap) {
        return;
    }

    const modalTitle = document.getElementById("detailModalLabel");
    const modalBody = document.getElementById("detailModalBody");
    const detailModal = new window.bootstrap.Modal(modalElement);

    // Keep the modal responsive while the detail request is in flight.
    function renderLoadingState() {
        modalTitle.textContent = "Loading details";
        modalBody.innerHTML = '<div class="text-muted">Loading details...</div>';
    }

    function renderErrorState() {
        modalTitle.textContent = "Unable to load details";
        modalBody.innerHTML = '<div class="alert alert-danger mb-0">Could not load the detail information.</div>';
    }

    function renderPayload(payload) {
        modalTitle.textContent = payload.title || "Details";
        const fields = Array.isArray(payload.fields) ? payload.fields : [];
        modalBody.innerHTML = fields.map((field) => `
            <div class="detail-modal-field">
                <div class="detail-modal-label">${escapeHtml(field.label || "")}</div>
                <div class="detail-modal-value">${escapeHtml(field.value || "Not set")}</div>
            </div>
        `).join("");
    }

    // Delegate click handling so dynamically rendered triggers work as well.
    document.addEventListener("click", async (event) => {
        const trigger = event.target.closest("[data-detail-trigger]");
        if (!trigger) {
            return;
        }

        event.preventDefault();
        const detailUrl = trigger.getAttribute("data-detail-url");
        renderLoadingState();
        detailModal.show();

        try {
            const response = await fetch(detailUrl, {
                headers: {
                    "X-Requested-With": "XMLHttpRequest",
                    "Accept": "application/json",
                },
            });
            if (!response.ok) {
                throw new Error(`Request failed with status ${response.status}`);
            }
            const payload = await response.json();
            renderPayload(payload);
        } catch (error) {
            renderErrorState();
        }
    });

    modalElement.addEventListener("hidden.bs.modal", () => {
        modalTitle.textContent = "Details";
        modalBody.innerHTML = '<div class="text-muted">Loading details...</div>';
    });
}




// Validate the comma-separated teacher ID input before the form submits.
function initAdminCourseFormValidation() {
    if (!document.body.classList.contains("page-admin-course-form")) {
        return;
    }

    const form = document.querySelector("[data-course-form]");
    const teacherIdsInput = document.getElementById("id_teacher_staff_ids");
    const feedback = document.getElementById("teacher-ids-live-feedback");
    if (!form || !teacherIdsInput || !feedback) {
        return;
    }

    const teacherIdPattern = /^T\d{8}$/;

    // Split, trim, and discard empty fragments from the admin input string.
    function parseTeacherIds(value) {
        return value
            .split(",")
            .map((item) => item.trim())
            .filter(Boolean);
    }

    function teacherIdsAreValid(value) {
        const normalized = value.trim();
        if (!normalized) {
            return true;
        }
        return parseTeacherIds(normalized).every((item) => teacherIdPattern.test(item));
    }

    function renderTeacherIdValidation() {
        const showError = !teacherIdsAreValid(teacherIdsInput.value);
        teacherIdsInput.classList.toggle("is-invalid", showError);
        feedback.classList.toggle("d-block", showError);
        return !showError;
    }

    teacherIdsInput.addEventListener("input", renderTeacherIdValidation);
    teacherIdsInput.addEventListener("blur", renderTeacherIdValidation);

    form.addEventListener("submit", (event) => {
        if (!renderTeacherIdValidation()) {
            event.preventDefault();
        }
    });
}

// Require an explicit confirmation before submitting a withdraw request.
function initStudentWithdrawConfirmation() {
    if (!document.body.classList.contains("page-student-dashboard")) {
        return;
    }

    const modalElement = document.getElementById("withdrawConfirmModal");
    const confirmButton = document.getElementById("withdrawConfirmSubmit");
    const courseNameElement = document.getElementById("withdrawConfirmCourseName");
    const withdrawButtons = document.querySelectorAll("[data-withdraw-course]");
    if (!modalElement || !confirmButton || !courseNameElement || !withdrawButtons.length || !window.bootstrap) {
        return;
    }

    const withdrawModal = new window.bootstrap.Modal(modalElement);
    let pendingForm = null;

    withdrawButtons.forEach((button) => {
        button.addEventListener("click", (event) => {
            event.preventDefault();
            pendingForm = button.closest("form");
            courseNameElement.textContent = button.getAttribute("data-withdraw-course") || "This course";
            withdrawModal.show();
        });
    });

    confirmButton.addEventListener("click", () => {
        if (!pendingForm) {
            return;
        }

        const formToSubmit = pendingForm;
        pendingForm = null;
        withdrawModal.hide();
        formToSubmit.submit();
    });

    modalElement.addEventListener("hidden.bs.modal", () => {
        pendingForm = null;
        courseNameElement.textContent = "-";
    });
}

// Reuse a single modal to show course details for any course row on the student page.
function initStudentCourseDetailModal() {
    if (!document.body.classList.contains("page-student-dashboard")) {
        return;
    }

    const modalElement = document.getElementById("studentCourseDetailModal");
    const modalTitle = document.getElementById("studentCourseDetailLabel");
    const modalBody = document.getElementById("studentCourseDetailBody");
    if (!modalElement || !modalTitle || !modalBody || !window.bootstrap) {
        return;
    }

    // Reuse one modal instance for all course detail triggers.
    const detailModal = new window.bootstrap.Modal(modalElement);

    function renderLoadingState() {
        modalTitle.textContent = "Course Details";
        modalBody.innerHTML = '<div class="text-muted">Loading details...</div>';
    }

    function renderErrorState() {
        modalTitle.textContent = "Unable to Load Course";
        modalBody.innerHTML = '<div class="alert alert-danger mb-0">Could not load the course details.</div>';
    }

    function renderCourseDetail(course) {
        // Fill the modal with the course data returned by the detail API.
        modalTitle.textContent = course.course_name || "Course Details";
        modalBody.innerHTML = `
            <div class="student-course-summary">
                <div class="d-flex justify-content-between align-items-start gap-3 flex-wrap mb-4">
                    <div>
                        <h3 class="h4 mb-1 fw-bold">${escapeHtml(course.course_name || "Course Details")}</h3>
                    </div>
                    <span class="badge rounded-pill text-bg-light student-course-summary-badge">
                        ${escapeHtml(course.delivery_mode || "Not set")}
                    </span>
                </div>

                <div class="row g-3 mb-3">
                    <div class="col-12 col-md-6 col-xl-3">
                        <div class="student-summary-card">
                            <div class="student-summary-label">Course Code</div>
                            <div class="student-summary-value">${escapeHtml(course.course_code || "Not set")}</div>
                        </div>
                    </div>
                    <div class="col-12 col-md-6 col-xl-3">
                        <div class="student-summary-card">
                            <div class="student-summary-label">Credits</div>
                            <div class="student-summary-value">${escapeHtml(String(course.credits ?? "Not set"))}</div>
                        </div>
                    </div>
                    <div class="col-12 col-md-6 col-xl-3">
                        <div class="student-summary-card">
                            <div class="student-summary-label">Class Time</div>
                            <div class="student-summary-value">${escapeHtml(course.schedule || "Not set")}</div>
                        </div>
                    </div>
                    <div class="col-12 col-md-6 col-xl-3">
                        <div class="student-summary-card">
                            <div class="student-summary-label">Location</div>
                            <div class="student-summary-value">${escapeHtml(course.location || "Not set")}</div>
                        </div>
                    </div>
                    <div class="col-12 col-md-6 col-xl-4">
                        <div class="student-summary-card">
                            <div class="student-summary-label">Term Start Date</div>
                            <div class="student-summary-value">${escapeHtml(course.start_date || "Not set")}</div>
                        </div>
                    </div>
                    <div class="col-12 col-md-6 col-xl-4">
                        <div class="student-summary-card">
                            <div class="student-summary-label">Term End Date</div>
                            <div class="student-summary-value">${escapeHtml(course.end_date || "Not set")}</div>
                        </div>
                    </div>
                    <div class="col-12 col-md-6 col-xl-4">
                        <div class="student-summary-card">
                            <div class="student-summary-label">Enrollment</div>
                            <div class="student-summary-value">${escapeHtml(`${course.enrolled_count}/${course.capacity}`)}</div>
                        </div>
                    </div>
                    <div class="col-12">
                        <div class="student-summary-card">
                            <div class="student-summary-label">Instructor</div>
                            <div class="student-summary-value">${escapeHtml(course.teacher_name || "Unassigned")}</div>
                        </div>
                    </div>
                </div>

                <div class="student-summary-card">
                    <div class="student-summary-label">Course Description</div>
                    <div class="student-summary-value">${escapeHtml(course.description || "Not set")}</div>
                </div>
            </div>
        `;
    }

    document.addEventListener("click", async (event) => {
        const trigger = event.target.closest("[data-course-detail-trigger]");
        if (!trigger) {
            return;
        }

        event.preventDefault();
        // Each trigger carries the API URL for its course.
        const detailUrl = trigger.getAttribute("data-course-detail-url");
        if (!detailUrl) {
            return;
        }

        renderLoadingState();
        detailModal.show();

        try {
            // Request the selected course detail, then render it into the modal.
            const response = await fetch(detailUrl, {
                headers: {
                    "X-Requested-With": "XMLHttpRequest",
                    "Accept": "application/json",
                },
            });
            if (!response.ok) {
                throw new Error(`Request failed with status ${response.status}`);
            }

            const payload = await response.json();
            renderCourseDetail(payload?.data?.course || {});
        } catch (error) {
            renderErrorState();
        }
    });

    modalElement.addEventListener("hidden.bs.modal", () => {
        renderLoadingState();
    });
}

// Initialize only the page-specific behaviors that match the current body class.
document.addEventListener("DOMContentLoaded", () => {
    initAdminCourseDetailModal();
    initAdminCourseFormValidation();
    initStudentWithdrawConfirmation();
    initStudentCourseDetailModal();
});
