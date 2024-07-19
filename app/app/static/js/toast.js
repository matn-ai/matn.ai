document.addEventListener('DOMContentLoaded', function () {
    var toastElements = document.querySelectorAll('.toast');
    toastElements.forEach(function (toastElement) {
        var toast = new bootstrap.Toast(toastElement);
        toast.show();
    });
});

document.addEventListener('click', function(event) {
    if (event.target.classList.contains('star')) {
        let stars = document.querySelectorAll('.star');
        let starValue = parseInt(event.target.getAttribute('data-star'));

        stars.forEach(star => {
            if (parseInt(star.getAttribute('data-star')) <= starValue) {
                star.classList.add('selected');
            } else {
                star.classList.remove('selected');
            }
        });
    }
});

// Function to create and show a toast
function showToast(message, type = 'primary', delay = 5000) {
    const toastContainer = document.getElementById('toast-container');

    const toastHtml = `
        <div class="toast text-bg-${type} border-0" role="alert" aria-live="assertive" aria-atomic="true" data-bs-delay="${delay}">
            <div class="d-flex">
                <div class="toast-body">
                    ${message}
                </div>
                <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button>
            </div>
        </div>
    `;

    toastContainer.insertAdjacentHTML('beforeend', toastHtml);

    const toastElement = toastContainer.lastElementChild;
    const toast = new bootstrap.Toast(toastElement);
    toast.show();

    toastElement.addEventListener('hidden.bs.toast', () => {
        toastElement.remove();
    });
}