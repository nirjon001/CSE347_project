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

    var userMenu = document.getElementById('user-menu');
    var userMenuToggle = document.getElementById('user-menu-toggle');
    if (userMenu && userMenuToggle) {
        function setMenu(open) {
            userMenu.classList.toggle('open', open);
            userMenuToggle.setAttribute('aria-expanded', open ? 'true' : 'false');
        }
        userMenuToggle.addEventListener('click', function (e) {
            e.stopPropagation();
            setMenu(!userMenu.classList.contains('open'));
        });
        document.addEventListener('click', function (e) {
            if (!userMenu.contains(e.target)) {
                setMenu(false);
            }
        });
        document.addEventListener('keydown', function (e) {
            if (e.key === 'Escape') {
                setMenu(false);
            }
        });
    }

    var sidebar = document.getElementById('sidebar');
    var sidebarToggle = document.getElementById('sidebar-toggle');
    var sidebarClose = document.getElementById('sidebar-close');
    var sidebarOverlay = document.getElementById('sidebar-overlay');
    if (sidebar && sidebarToggle) {
        function setSidebar(open) {
            document.body.classList.toggle('sidebar-open', open);
            sidebarToggle.setAttribute('aria-expanded', open ? 'true' : 'false');
            if (sidebarOverlay) {
                sidebarOverlay.hidden = false;
                sidebarOverlay.classList.toggle('show', open);
            }
        }
        sidebarToggle.addEventListener('click', function (e) {
            e.stopPropagation();
            setSidebar(!document.body.classList.contains('sidebar-open'));
        });
        if (sidebarClose) {
            sidebarClose.addEventListener('click', function () {
                setSidebar(false);
            });
        }
        if (sidebarOverlay) {
            sidebarOverlay.addEventListener('click', function () {
                setSidebar(false);
            });
        }
        sidebar.addEventListener('click', function (e) {
            if (e.target.closest('.sidebar-nav a')) {
                setSidebar(false);
            }
        });
        document.addEventListener('keydown', function (e) {
            if (e.key === 'Escape' && document.body.classList.contains('sidebar-open')) {
                setSidebar(false);
            }
        });
    }
});
