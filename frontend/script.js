document.addEventListener("DOMContentLoaded", () => {
  const bookButtons = document.querySelectorAll(".book-btn");
  const modal = document.getElementById("unit-modal");
  const modalTitle = document.getElementById("modal-title");
  const modalDescription = document.getElementById("modal-description");
  const closeModal = document.querySelector(".close-modal");

  // Booking functionality
/*  bookButtons.forEach((button) => {
    button.addEventListener("click", (event) => {
      const unit = event.target.closest(".unit");
      if (!unit.classList.contains("booked")) {
        unit.classList.add("booked");
        button.textContent = "Booked";
        button.disabled = true;
        alert(`${unit.querySelector("h3").textContent} has been booked!`);
      }
    });
  });*/

  // Open modal with unit details
  document.querySelectorAll(".unit").forEach((unit) => {
    unit.addEventListener("click", (event) => {
      if (!event.target.classList.contains("book-btn")) {
        modal.classList.remove("hidden");
        modalTitle.textContent = unit.querySelector("h3").textContent;
        modalDescription.textContent = `Details for ${unit.querySelector(
          "h3"
        ).textContent}. Customize this description as needed.`;
      }
    });
  });

  // Close modal
  closeModal.addEventListener("click", () => {
    modal.classList.add("hidden");
  });

  modal.addEventListener("click", (event) => {
    if (event.target === modal) {
      modal.classList.add("hidden");
    }
  });
});
// Open the booking form modal
function openBookingForm(unitId) {
  // Populate unit information in the form (you can expand this later with more dynamic content)
  const unitSizeSelect = document.getElementById('unit-size');
  const startDateInput = document.getElementById('start-date');
  const bookingDurationInput = document.getElementById('booking-duration');
  
  // Optionally, you can dynamically set data based on the unitId
  // For now, we're just opening the modal with default options.

  document.getElementById('booking-modal').style.display = "block";
}

// Close the booking form modal
function closeBookingForm() {
  document.getElementById('booking-modal').style.display = "none";
}

// Handle the form submission
document.getElementById('booking-form').addEventListener('submit', function(e) {
  e.preventDefault(); // Prevent form submission

  const unitSize = document.getElementById('unit-size').value;
  const startDate = document.getElementById('start-date').value;
  const duration = document.getElementById('booking-duration').value;

  // Display confirmation message or handle booking logic
  alert(`Booking Confirmed! \nSize: ${unitSize} \nStart Date: ${startDate} \nDuration: ${duration} days`);

  // Close the modal after submission
  closeBookingForm();
});


  