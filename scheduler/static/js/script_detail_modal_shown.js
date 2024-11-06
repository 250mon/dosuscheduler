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
      const modalUpdateBtn = $("#detailModalUpdateBtn");
      const updateForm = $("#updateDetailForm");
      const baseUpdateUrl = updateForm.attr("action");
      const updateUrl = baseUpdateUrl.replace("0", dosusessId);
      updateForm.attr("action", updateUrl);

      const btnBaseUpdateUrl = modalUpdateBtn.attr("href");
      const btnUpdateUrl = btnBaseUpdateUrl.replace("0", dosusessId);
      modalUpdateBtn.attr("href", btnUpdateUrl);

      $("#modalDetailId").val(dosusessId);
      $("#modalUpdateId").val(dosusessId);
      $("#modalDeleteId").val(dosusessId);

      const fetchDosuSess = async (id) => {
        fetch(`/dosusess/get_dosusess/${id}`)
          .then((response) => response.json())
          .then((data) => {
            sess = data.dosusess;
            $("#modalDetailMrn").text(sess.mrn);
            $("#modalDetailPatientName")
              .attr("href", `/patient/detail/${sess.patient_id}`)
              .text(sess.patient_name);
            $("#modalDetailPatientNote").text(sess.patient_note);
            $("#modalDetailTel").text(sess.tel);
            $("#modalDetailWorkerName").text(sess.worker_name);
            $("#modalDetailDosusessDate").text(sess.date_display);
            $("#modalDetailSlot").text(sess.slot_display);
            $("#modalDetailDosutype").text(sess.dosutype_name);
            $(`#modalDetailStatus-${sess.status}`).attr("checked", true);
            $("#modalDetailNote").text(sess.note);
            $("#modalDetailIsFirstCheck").attr("checked", sess.is_first);
            const sess_date = new Date(sess.date);
            if (
              userPrivilege > 3 ||
              (userPrivilege == 3 && isNoEarlierThanFirstday(sess_date)) ||
              isNoEarlierThanToday(sess_date)
            ) {
              if (sess.status === "active") {
                $("#detailModalUpdateBtn").css("display", "");
                $("#detailModalSaveBtn").css("display", "");
                $("#detailModalDeleteBtn").css("display", "");
              } else {
                $("#detailModalUpdateBtn").css("display", "none");
                $("#detailModalDeleteBtn").css("display", "none");
              }
            } else {
              $("#detailModalUpdateBtn").css("display", "none");
              $("#detailModalSaveBtn").css("display", "none");
              $("#detailModalDeleteBtn").css("display", "none");
            }
          });
      };

      fetchDosuSess(dosusessId);
    });
  }
});

const isNoEarlierThanToday = (date) => {
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  date.setHours(0, 0, 0, 0);
  return date >= today;
};

const isNoEarlierThanFirstday = (date) => {
  const today = new Date();
  const firstDayOfMonth = new Date(today.getFullYear(), today.getMonth(), 1);
  firstDayOfMonth.setHours(0, 0, 0, 0);
  date.setHours(0, 0, 0, 0);
  return date >= firstDayOfMonth;
};
