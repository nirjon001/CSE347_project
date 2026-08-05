document.addEventListener('DOMContentLoaded', function () {
    document.querySelectorAll('form[data-confirm]').forEach(function (form) {
        form.addEventListener('submit', function (e) {
            if (!window.confirm(form.dataset.confirm)) {
                e.preventDefault();
            }
        });
    });

    document.querySelectorAll('.toggle-password').forEach(function (btn) {
        btn.addEventListener('click', function () {
            var input = btn.closest('.password-wrap').querySelector('input');
            var show = input.type === 'password';
            input.type = show ? 'text' : 'password';
            btn.querySelector('.icon-eye').style.display = show ? 'none' : '';
            btn.querySelector('.icon-eye-off').style.display = show ? '' : 'none';
            btn.setAttribute('aria-label', show ? 'Hide password' : 'Show password');
        });
    });

    var studentSelect = document.querySelector('select[data-role="gender-filter"]');
    var roomSelect = document.querySelector('select[data-role="gender-options"]');
    if (studentSelect && roomSelect) {
        function filterRooms() {
            var gender = studentSelect.selectedOptions[0] ? studentSelect.selectedOptions[0].dataset.gender : '';
            var visible = [];
            Array.prototype.forEach.call(roomSelect.options, function (opt) {
                var match = !gender || opt.dataset.gender === gender;
                opt.hidden = !match;
                if (match) visible.push(opt);
            });
            if (visible.length) {
                visible[0].selected = true;
            }
        }
        studentSelect.addEventListener('change', filterRooms);
        filterRooms();
    }
});
