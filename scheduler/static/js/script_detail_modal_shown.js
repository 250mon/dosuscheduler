$(document).ready(function () {
  const dosusessListContainer = document.querySelector(
    ".dosusess-list-container",
  );
  const userPrivilege = dosusessListContainer.getAttribute(
    "data-user_privilege",
  );

  const detailDosuSessModal = document.getElementById("detailDosuSessModal");

  let sess = {};

  if (detailDosuSessModal) {
    detailDosuSessModal.addEventListener("show.bs.modal", (event) => {
      // Button that triggered the modal
      const button = event.relatedTarget;
      // Extract info from data-bs-* attributes
      const dosusessId = button.getAttribute("data-bs-dosusess-id");

      // make an update url to include dosusessId
      const modalUpdateBtn = $("#detail-modal-update-btn");
      const updateForm = $("#updateDetailForm");
      const baseUpdateUrl = updateForm.attr("action");
      const updateUrl = baseUpdateUrl.replace("0", dosusessId);
      updateForm.attr("action", updateUrl);

      const btnBaseUpdateUrl = modalUpdateBtn.attr("href");
      const btnUpdateUrl = btnBaseUpdateUrl.replace("0", dosusessId);
      modalUpdateBtn.attr("href", btnUpdateUrl);

      $("#modal-detail-id").val(dosusessId);
      $("#modal-update-id").val(dosusessId);
      $("#modal-delete-id").val(dosusessId);

      const fetchDosuSess = async (id) => {
        fetch(`/dosusess/get_dosusess/${id}`)
          .then((response) => response.json())
          .then((data) => {
            sess = data.dosusess;
            $("#modal-detail-mrn").text(sess.mrn);
            $("#modal-detail-patient-name")
              .attr("href", `/patient/detail/${sess.patient_id}`)
              .text(sess.patient_name);
            $("#modal-detail-patient-note").text(sess.patient_note);
            $("#modal-detail-tel").text(sess.tel);
            $("#modal-detail-worker-name").text(sess.worker_name);
            $("#modal-detail-dosusess-date").text(sess.date_display);
            $("#modal-detail-slot").text(sess.slot_display);
            $("#modal-detail-dosutype").text(sess.dosutype_name);
            $(`#modal-detail-status-${sess.status}`).prop("checked", true);
            $("#modal-detail-note").text(sess.note);
            if (
              userPrivilege > 2 ||
              isDateNoEarlierThanToday(new Date(sess.date))
            ) {
              if (sess.status === "active") {
                $("#detail-modal-update-btn").css("display", "");
                $("#detail-modal-save-btn").css("display", "");
                $("#detail-modal-delete-btn").css("display", "");
              } else {
                $("#detail-modal-update-btn").css("display", "none");
                $("#detail-modal-delete-btn").css("display", "none");
              }
            } else {
              $("#detail-modal-update-btn").css("display", "none");
              $("#detail-modal-save-btn").css("display", "none");
              $("#detail-modal-delete-btn").css("display", "none");
            }
          });
      };

      fetchDosuSess(dosusessId);
    });
  }
});

const isDateNoEarlierThanToday = (date) => {
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  date.setHours(0, 0, 0, 0);
  return date >= today;
};
