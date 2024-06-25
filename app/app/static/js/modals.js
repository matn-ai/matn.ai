function createAndOpenModal(modalId, modalTitle, modalBodyContent, modalFooterContent) {
    // Remove any previously created modals to avoid duplicates
    $('#' + modalId).remove();
  
    // Create the modal HTML
    const modalHTML = `
      <div class="modal fade" id="${modalId}" tabindex="-1" aria-labelledby="${modalId}Label" aria-hidden="true">
        <div class="modal-dialog">
          <div class="modal-content">
            <div class="modal-header">
              <h5 class="modal-title" id="${modalId}Label">${modalTitle}</h5>
              <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
            </div>
            <div class="modal-body">${modalBodyContent}</div>
            <div class="modal-footer">${modalFooterContent}</div>
          </div>
        </div>
      </div>
    `;
  
    // Append the modal HTML to the container
    $('body').append(modalHTML);
  
    // Initialize and show the modal
    const myModal = new bootstrap.Modal(document.getElementById(modalId));
    myModal.show();
  }