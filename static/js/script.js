// Shared static entry point for template scripts.

function escapeHtml(value) {
    return String(value)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#39;");
}

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

function initStudentWithdrawConfirmation() {
    if (!document.body.classList.contains("page-student-dashboard")) {
        return;
    }

    const withdrawButtons = document.querySelectorAll("[data-withdraw-course]");
    if (!withdrawButtons.length) {
        return;
    }

    withdrawButtons.forEach((button) => {
        button.addEventListener("click", (event) => {
            const courseName = button.getAttribute("data-withdraw-course") || "this course";
            // Require an explicit confirmation before allowing a drop action.
            const confirmed = window.confirm(`Are you sure you want to drop "${courseName}"?`);

            if (!confirmed) {
                event.preventDefault();
                return;
            }

            const form = button.closest("form");
            if (form) {
                // Submit manually after confirmation so the browser does not treat this as an accidental click.
                form.submit();
            }
        });
    });
}

document.addEventListener("DOMContentLoaded", () => {
    initAdminCourseDetailModal();
    initAdminCourseFormValidation();
    initStudentWithdrawConfirmation();
});
