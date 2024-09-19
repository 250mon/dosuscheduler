function validatePatientForm() {
  let pt_id = document.getElementById("pt_id").value;
  js;
  let name = document.getElementById("name").value;
  let sex = document.querySelector('input[name="sex"]:checked');
  let birthday = document.getElementById("birthday").value;
  let tel = document.getElementById("tel").value;

  if (!pt_id || !name || !sex) {
    alert("Please fill out all required fields.");
    return false;
  }

  let birthdayPattern = /^\d{4}-\d{2}-\d{2}$/;
  if (birthday && !birthdayPattern.test(birthday)) {
    alert("Please enter a valid birthday in the format YYYY-MM-DD.");
    return false;
  }

  return true;
}

function validateWorkerForm() {
  let name = document.getElementById("name").value;
  let room = document.getElementById("room").value;

  if (!name || !room) {
    alert("Please fill out all required fields.");
    return false;
  }

  return true;
}

// Get all radio buttons with the name 'status-filter'
const statusRadios = document.querySelectorAll('input[name="new-status"]');
// Get the form element
const form = document.getElementById("status-filter-form");
// Add an event listener to each radio button
statusRadios.forEach((radio) => {
  radio.addEventListener("change", () => {
    // Submit the form when the radio button changes
    form.submit();
  });
});
