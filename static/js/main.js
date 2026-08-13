document.addEventListener('DOMContentLoaded', function () {
    document.querySelectorAll('form[data-confirm]').forEach(function (form) {
        form.addEventListener('submit', function (e) {
            if (!window.confirm(form.dataset.confirm)) {
                e.preventDefault();
            }
        });
    });

    function badgeClass(status) {
        var map = {
            'Paid': 'badge-green', 'Unpaid': 'badge-yellow', 'Overdue': 'badge-red',
            'Pending': 'badge-yellow', 'In Progress': 'badge-blue', 'Resolved': 'badge-green',
            'Approved': 'badge-green', 'Rejected': 'badge-red',
            'Arrived': 'badge-yellow', 'Collected': 'badge-green',
            'Open': 'badge-red', 'Out': 'badge-yellow', 'Returned': 'badge-green',
            'Present': 'badge-green', 'Absent': 'badge-red', 'Leave': 'badge-blue'
        };
        return map[status] || 'badge-green';
    }

    function flashAjax(category, message) {
        var list = document.querySelector('.flashes');
        if (!list) {
            list = document.createElement('ul');
            list.className = 'flashes';
            var container = document.querySelector('.container');
            if (container) container.insertBefore(list, container.firstChild);
        }
        var li = document.createElement('li');
        li.className = category;
        li.textContent = message;
        list.appendChild(li);
        setTimeout(function () { li.remove(); }, 6000);
    }

    document.querySelectorAll('form[data-ajax]').forEach(function (form) {
        form.addEventListener('submit', function (e) {
            e.preventDefault();
            var btn = e.submitter && e.submitter.type === 'submit' ? e.submitter : form.querySelector('button[type="submit"]');
            if (btn) btn.disabled = true;
            var fd = new FormData(form);
            if (e.submitter && e.submitter.name) fd.append(e.submitter.name, e.submitter.value);
            fetch(form.action || window.location.href, {
                method: 'POST',
                headers: { 'X-Requested-With': 'XMLHttpRequest' },
                body: fd
            }).then(function (resp) {
                return resp.json().catch(function () { return { ok: false, message: 'Server error. Please refresh.' }; });
            }).then(function (data) {
                if (btn) btn.disabled = false;
                if (!data.ok) {
                    flashAjax('danger', data.message || 'Something went wrong.');
                    return;
                }
                flashAjax('success', data.message || 'Done.');
                applyAjaxResult(form, data);
            }).catch(function () {
                if (btn) btn.disabled = false;
                flashAjax('danger', 'Could not reach the server. Please refresh and try again.');
            });
        });
    });

    function applyAjaxResult(form, data) {
        var kind = form.getAttribute('data-ajax');
        if (kind === 'readall') {
            document.querySelectorAll('.notif-item.unread').forEach(function (item) {
                item.classList.remove('unread');
            });
            var unreadChip = document.querySelector('.chip[data-filter="unread"]');
            if (unreadChip) unreadChip.remove();
            var badge = document.querySelector('.notif-link .notif-badge');
            if (badge) badge.remove();
            return;
        }
        var row = form.closest('tr');
        if (row) {
            var badge = row.querySelector('.badge');
            if (badge && data.status) {
                badge.textContent = data.status;
                badge.className = 'badge ' + badgeClass(data.status);
            }
            if (kind === 'return') {
                row.remove();
                return;
            }
            if (kind === 'collect' || kind === 'resolve' || kind === 'messoff') {
                var muted = document.createElement('span');
                muted.className = 'muted';
                muted.textContent = kind === 'collect' ? 'Collected by you'
                                   : kind === 'resolve' ? 'Resolved'
                                   : 'No action';
                form.replaceWith(muted);
                return;
            }
            if (kind === 'invoice') {
                var b = form.querySelector('button[type="submit"]');
                if (b) b.textContent = 'Mark ' + (data.status === 'Paid' ? 'Unpaid' : 'Paid');
            }
        }
    }

    var unreadPopup = document.getElementById('unread-popup');
    var unreadPopupClose = document.getElementById('unread-popup-close');
    var unreadPopupLater = document.getElementById('unread-popup-later');
    if (unreadPopup) {
        function closeUnreadPopup() {
            unreadPopup.style.display = 'none';
        }
        if (unreadPopupClose) unreadPopupClose.addEventListener('click', closeUnreadPopup);
        if (unreadPopupLater) unreadPopupLater.addEventListener('click', closeUnreadPopup);
        unreadPopup.addEventListener('click', function (e) {
            if (e.target === unreadPopup) closeUnreadPopup();
        });
        document.addEventListener('keydown', function (e) {
            if (e.key === 'Escape') closeUnreadPopup();
        });
    }

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
