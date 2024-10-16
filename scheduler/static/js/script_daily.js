import {
  updateDateDisplay,
  formatDate,
  generateTable,
  fetchSchedule,
  handleAvailableSlotClick,
  getSlotClickHandler,
} from "./utils_daily.js";

const realSlotClickHandler = (event, timeSlot) => {
  // Notify the server which time slot is clicked
  // The server will render the 'dosusess.select_patient_to_create_dosusess' page
  const csrf_token = $('meta[name="csrf_token"]').attr("content");

  // Create a form element
  const form = document.createElement("form");
  form.method = "POST";
  form.action = "/dosusess/available_slot_selected";

  // Add form fields with the parameters
  const sess_date = formatDate(timeSlot.date);
  const room = timeSlot["room"];
  const slot = timeSlot["slot"];
  const params = { csrf_token, sess_date, room, slot };
  for (const key in params) {
    if (params.hasOwnProperty(key)) {
      const hiddenField = document.createElement("input");
      hiddenField.type = "hidden";
      hiddenField.name = key;
      hiddenField.value = params[key];
      form.appendChild(hiddenField);
    }
  }
  // Append the form to the body and submit it
  document.body.appendChild(form);
  form.submit();
};

const applyScheduleData = (lastSlotIndex, schedule) => {
  handleAvailableSlotClick.handler_fn = realSlotClickHandler;
  $.each(schedule, (index, dosusessEntry) => {
    const {
      id,
      date,
      room,
      slot,
      slot_quantity,
      mrn,
      patient_name,
      note,
      status,
    } = dosusessEntry;

    const sess_date = new Date(date);
    const timeSlot = { date: sess_date, room: room, slot: slot };

    const roomContainer = room === 1 ? $("#room1") : $("#room2");
    // take slot_quantity
    let timeSlotDiv = roomContainer.find(`#slot${slot}`);
    // we maintain ids of each timeSlot to get slotClickHandler of the timeSlot
    const timeSlots = [timeSlot];
    for (let i = 1; i < slot_quantity; i++) {
      if (slot + i > lastSlotIndex) {
        break;
      }
      const additionalTSDiv = roomContainer.find(`#slot${slot + i}`);
      timeSlotDiv = timeSlotDiv.add(additionalTSDiv);
      const additionalTS = { date: sess_date, room: room, slot: slot + i };
      timeSlots.push(additionalTS);
    }

    const dosusessContainer = timeSlotDiv.find(".dosusess-container");

    $("<div>")
      .text(mrn || "")
      .addClass("mrn-display")
      .appendTo(dosusessContainer);
    $("<div>")
      .text(patient_name || "")
      .addClass("patient-name-display")
      .appendTo(dosusessContainer);
    $("<div>")
      .text(note || "")
      .addClass("note-display")
      .appendTo(dosusessContainer);

    // make the timeslots assigned to the schedule unavailable
    switch (status) {
      case "active":
        timeSlotDiv.removeClass("available");
        if (mrn === 0) {
          // block time slot
          timeSlotDiv.addClass("disabled");
        } else {
          timeSlotDiv.addClass("status-active");
        }
        for (let ts in timeSlots) {
          const clickHandler = getSlotClickHandler(timeSlots[ts]);
          // disable the default action of navigating to create session
          // instead, it pops a session detail modal
          timeSlotDiv.off("click", clickHandler);
        }
        break;
      case "canceled":
        timeSlotDiv.removeClass("empty").addClass("status-canceled");
        break;
      case "noshow":
        timeSlotDiv.removeClass("empty").addClass("status-noshow");
        break;
      default: // not reach here
        timeSlotDiv.addClass("status-default");
        break;
    }

    timeSlotDiv
      .attr("type", "button")
      .attr("data-bs-toggle", "modal")
      .attr("data-bs-target", "#detailDosuSessModal")
      .attr("data-bs-dosusess-id", id);
  });
};

$(document).ready(function () {
  const dosusessListContainer = $(".dosusess-list-container");
  const dateDisplay = $("#dateDisplay");
  const prevDateButton = $("#prevDay");
  const nextDateButton = $("#nextDay");
  const csrfToken = $('meta[name="csrf_token"]').attr("content");

  const userPrivilege = dosusessListContainer.data("user_privilege");
  const statusFilter = dosusessListContainer.data("status_filter");
  const currentDate = new Date(
    dosusessListContainer.data("year"),
    dosusessListContainer.data("month") - 1,
    dosusessListContainer.data("day"),
  );

  const changeDate = async (increment) => {
    currentDate.setDate(currentDate.getDate() + increment);
    if (currentDate.getDay() === 0) {
      // To skip Sundays
      currentDate.setDate(currentDate.getDate() + increment);
    }
    updateDateDisplay(currentDate, dateDisplay);

    const data = await fetchSchedule(csrfToken, currentDate);
    const timeslotConfig = data.timeslotConfig;
    const dSchedule = data.schedule;
    const lastSlotIndex = generateTable(
      userPrivilege,
      timeslotConfig,
      currentDate,
      statusFilter,
      getSlotClickHandler,
    );
    applyScheduleData(lastSlotIndex, dSchedule);
  };
  prevDateButton.on("click", () => changeDate(-1));
  nextDateButton.on("click", () => changeDate(1));

  try {
    changeDate(0);
  } catch (error) {
    console.error("Error loading schedule:", error);
  }
});
