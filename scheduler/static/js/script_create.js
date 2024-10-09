const createOptions = (dosutypeSelectEl, dosutypes, selected_id) => {
  // Check if dosutypes is an object and not empty
  if (
    typeof dosutypes !== "object" ||
    dosutypes === null ||
    Object.keys(dosutypes).length === 0
  ) {
    console.log("No dosutypes available or invalid data format");
    return;
  }

  Object.entries(dosutypes).forEach(([id, dosutype]) => {
    const { name } = dosutype;
    const optionEl = document.createElement("option");
    optionEl.setAttribute("value", id);
    const nameNode = document.createTextNode(name);
    optionEl.appendChild(nameNode);
    if (id === selected_id) {
      optionEl.setAttribute("selected", true);
    }
    dosutypeSelectEl.appendChild(optionEl);
  });
};

export const createDosutypeSelect = async (
  dosutypeSelectEl,
  pt_id,
  selected_id,
) => {
  try {
    const response = await fetch(`/dosutype/get_dosutypes/${pt_id}`);
    const data = await response.json();

    // Check if data.dosutypes exists and is an object
    const dosutypes =
      typeof data.dosutypes === "object" && data.dosutypes !== null
        ? data.dosutypes
        : {};
    createOptions(dosutypeSelectEl, dosutypes, selected_id);
  } catch (error) {
    console.error("Error fetching dosutypes:", error);
  }
};

const showDosuInfoInputBox = (btn) => {
  const dosuInfoInputContainer = document.getElementById("dosusess-info-input");
  dosuInfoInputContainer.classList.remove("d-none");

  // set input for patientId
  const patientId = btn.getAttribute("data-patient-id");
  const patientIdInput = document.getElementById("patient-id-input");
  patientIdInput.setAttribute("value", patientId);

  const dosutypeSelectEl = document.getElementById("dosutype-select");
  // different dosutypes are displayed depending on patientId
  createDosutypeSelect(dosutypeSelectEl, patientId);
};

document.addEventListener("DOMContentLoaded", () => {
  const buttons = document.querySelectorAll(".ptSelectBtn");
  buttons.forEach((button) => {
    button.addEventListener("click", (event) => {
      showDosuInfoInputBox(event.target);
    });
  });
});
