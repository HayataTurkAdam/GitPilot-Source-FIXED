import os
from pathlib import Path

import keyring
from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QFont
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel,
    QPushButton, QListWidget, QListWidgetItem, QStackedWidget, QFrame,
    QMessageBox, QFileDialog, QInputDialog, QLineEdit, QPlainTextEdit,
    QTableWidget, QTableWidgetItem, QHeaderView, QComboBox, QSplitter,
    QDialog, QFormLayout, QDialogButtonBox
)

from gitpilot.config import load_config, save_config
from gitpilot.git_service import GitError, is_repo, repo_info, run_git, clone_repo, commit_push, publish_folder
from gitpilot.github_api import GitHubClient, GitHubError
from gitpilot.ui.dialogs import AccountDialog, PublishDialog, ReleaseDialog

APP_NAME = "GitPilot"

DARK_STYLE = """
QWidget { background:#171923; color:#e6e8ef; font-family:'Segoe UI'; font-size:10pt; }
QMainWindow { background:#171923; }
QFrame#Sidebar { background:#11131b; border-right:1px solid #2b3040; }
QLabel#Brand { font-size:19pt; font-weight:700; color:#ffffff; padding:8px; }
QLabel#PageTitle { font-size:19pt; font-weight:650; color:#ffffff; }
QLabel#Muted { color:#9ba3b4; }
QPushButton { background:#292f40; border:1px solid #394158; border-radius:7px; padding:8px 13px; }
QPushButton:hover { background:#343d53; }
QPushButton#Primary { background:#5965d8; border-color:#6875ed; color:white; font-weight:600; }
QPushButton#Danger { background:#542d39; border-color:#754050; }
QListWidget, QTableWidget, QPlainTextEdit, QLineEdit, QComboBox {
  background:#202535; border:1px solid #343c50; border-radius:6px; padding:6px;
  selection-background-color:#4d5ac5;
}
QListWidget::item { padding:9px; border-radius:5px; }
QListWidget::item:selected { background:#303a59; color:white; }
QHeaderView::section { background:#252b3b; color:#bfc7d8; border:0; padding:8px; }
QTableWidget { gridline-color:#343c50; }
QPlainTextEdit { font-family:Consolas; }
QComboBox QAbstractItemView { background:#202535; selection-background-color:#4d5ac5; }
QFrame#Panel { background:#1d2231; border:1px solid #30384b; border-radius:10px; }
QScrollBar:vertical { background:#171923; width:10px; }
QScrollBar::handle:vertical { background:#3a4359; border-radius:4px; }
"""

def panel():
    frame = QFrame()
    frame.setObjectName("Panel")
    return frame

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("GitPilot — GitHub Repository Manager")
        self.resize(1320, 850)
        self.config = load_config()
        self.current_repo = None
        self.current_account = None
        self._build_ui()
        self._refresh_accounts()
        self._refresh_repositories()
        self._refresh_dashboard()

    def _build_ui(self):
        root = QWidget()
        self.setCentralWidget(root)
        outer = QHBoxLayout(root)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        sidebar = QFrame()
        sidebar.setObjectName("Sidebar")
        sidebar.setFixedWidth(225)
        side = QVBoxLayout(sidebar)
        side.setContentsMargins(14, 18, 14, 16)
        brand = QLabel("◈ GitPilot")
        brand.setObjectName("Brand")
        side.addWidget(brand)
        subtitle = QLabel("GITHUB WORKSPACE")
        subtitle.setObjectName("Muted")
        side.addWidget(subtitle)
        side.addSpacing(22)

        self.nav = QListWidget()
        self.nav.addItems(["Dashboard", "Repositories", "Accounts", "Releases", "Actions"])
        self.nav.setCurrentRow(0)
        self.nav.currentRowChanged.connect(self._navigate)
        side.addWidget(self.nav, 1)

        self.account_picker = QComboBox()
        self.account_picker.currentIndexChanged.connect(self._account_changed)
        side.addWidget(QLabel("ACTIVE ACCOUNT"))
        side.addWidget(self.account_picker)
        self.status_label = QLabel("Ready")
        self.status_label.setObjectName("Muted")
        side.addWidget(self.status_label)

        outer.addWidget(sidebar)
        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(26, 22, 26, 22)
        self.stack = QStackedWidget()
        content_layout.addWidget(self.stack)
        outer.addWidget(content, 1)

        self.pages = [
            self._dashboard_page(), self._repositories_page(), self._accounts_page(),
            self._releases_page(), self._actions_page()
        ]
        for page in self.pages:
            self.stack.addWidget(page)

    def _page_heading(self, title, subtitle):
        box = QVBoxLayout()
        title_label = QLabel(title)
        title_label.setObjectName("PageTitle")
        sub = QLabel(subtitle)
        sub.setObjectName("Muted")
        box.addWidget(title_label)
        box.addWidget(sub)
        box.addSpacing(12)
        return box

    def _dashboard_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.addLayout(self._page_heading("Dashboard", "Your local repositories and GitHub activity at a glance."))
        grid = QGridLayout()
        self.stat_repos = self._stat_card("Local repositories", "0")
        self.stat_accounts = self._stat_card("Connected accounts", "0")
        self.stat_changes = self._stat_card("Repositories with changes", "0")
        self.stat_remotes = self._stat_card("Connected remotes", "0")
        for i, card in enumerate([self.stat_repos, self.stat_accounts, self.stat_changes, self.stat_remotes]):
            grid.addWidget(card, i // 2, i % 2)
        layout.addLayout(grid)
        layout.addSpacing(14)
        layout.addWidget(QLabel("Quick actions"))
        actions = QHBoxLayout()
        for label, slot in [
            ("＋ Add repository", self.add_repository),
            ("⇩ Clone repository", self.clone_repository),
            ("⇧ Publish folder", self.publish_new_folder),
            ("↻ Refresh", self.refresh_all)
        ]:
            b = QPushButton(label)
            b.clicked.connect(slot)
            actions.addWidget(b)
        layout.addLayout(actions)
        layout.addStretch()
        return page

    def _stat_card(self, title, value):
        f = panel()
        l = QVBoxLayout(f)
        t = QLabel(title); t.setObjectName("Muted")
        v = QLabel(value); v.setStyleSheet("font-size:25pt;font-weight:700;color:white;")
        l.addWidget(t); l.addWidget(v)
        f.value_label = v
        return f

    def _repositories_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.addLayout(self._page_heading("Repositories", "Inspect local changes, commit and push your projects."))
        toolbar = QHBoxLayout()
        for label, slot in [
            ("Add local", self.add_repository), ("Clone", self.clone_repository),
            ("Publish folder", self.publish_new_folder), ("Remove", self.remove_repository),
            ("Refresh", self.refresh_repository_view)
        ]:
            b = QPushButton(label)
            if label == "Publish folder":
                b.setObjectName("Primary")
            b.clicked.connect(slot)
            toolbar.addWidget(b)
        layout.addLayout(toolbar)

        split = QSplitter(Qt.Horizontal)
        self.repo_list = QListWidget()
        self.repo_list.currentItemChanged.connect(self._repo_selected)
        split.addWidget(self.repo_list)

        detail = QWidget()
        d = QVBoxLayout(detail)
        self.repo_title = QLabel("Select a repository")
        self.repo_title.setStyleSheet("font-size:15pt;font-weight:600;")
        self.repo_meta = QLabel("No repository selected")
        self.repo_meta.setObjectName("Muted")
        d.addWidget(self.repo_title); d.addWidget(self.repo_meta)
        self.file_table = QTableWidget(0, 2)
        self.file_table.setHorizontalHeaderLabels(["Status", "File"])
        self.file_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.file_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        d.addWidget(self.file_table, 1)
        self.commit_message = QLineEdit()
        self.commit_message.setPlaceholderText("Commit message…")
        d.addWidget(self.commit_message)
        row = QHBoxLayout()
        self.stage_button = QPushButton("Stage all")
        self.stage_button.clicked.connect(self.stage_all)
        row.addWidget(self.stage_button)
        self.commit_button = QPushButton("Commit & Push")
        self.commit_button.setObjectName("Primary")
        self.commit_button.clicked.connect(self.commit_and_push)
        row.addWidget(self.commit_button)
        d.addLayout(row)
        self.repo_log = QPlainTextEdit()
        self.repo_log.setReadOnly(True)
        self.repo_log.setMaximumHeight(115)
        self.repo_log.setPlaceholderText("Git operation output…")
        d.addWidget(self.repo_log)
        split.addWidget(detail)
        split.setSizes([280, 800])
        layout.addWidget(split, 1)
        return page

    def _accounts_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.addLayout(self._page_heading("Accounts", "Connect multiple GitHub identities securely."))
        row = QHBoxLayout()
        add = QPushButton("＋ Add account"); add.setObjectName("Primary"); add.clicked.connect(self.add_account)
        remove = QPushButton("Remove selected"); remove.clicked.connect(self.remove_account)
        row.addWidget(add); row.addWidget(remove); row.addStretch()
        layout.addLayout(row)
        self.account_list = QListWidget()
        layout.addWidget(self.account_list)
        note = QLabel("Access tokens are stored in Windows Credential Manager using the system keyring.")
        note.setObjectName("Muted")
        layout.addWidget(note)
        return page

    def _releases_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.addLayout(self._page_heading("Releases", "Create versioned GitHub releases for a selected repository."))
        self.release_repo = QComboBox()
        layout.addWidget(QLabel("Repository"))
        layout.addWidget(self.release_repo)
        b = QPushButton("＋ Create release"); b.setObjectName("Primary"); b.clicked.connect(self.create_release)
        layout.addWidget(b, alignment=Qt.AlignLeft)
        self.release_info = QPlainTextEdit()
        self.release_info.setReadOnly(True)
        self.release_info.setPlaceholderText("Release results will appear here.")
        layout.addWidget(self.release_info, 1)
        return page

    def _actions_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.addLayout(self._page_heading("GitHub Actions", "Inspect recent workflow runs and rerun failed jobs."))
        self.actions_repo = QComboBox()
        layout.addWidget(QLabel("Repository"))
        layout.addWidget(self.actions_repo)
        row = QHBoxLayout()
        refresh = QPushButton("Refresh runs"); refresh.clicked.connect(self.load_workflow_runs)
        rerun = QPushButton("Rerun failed jobs"); rerun.setObjectName("Primary"); rerun.clicked.connect(self.rerun_selected)
        row.addWidget(refresh); row.addWidget(rerun); row.addStretch()
        layout.addLayout(row)
        self.runs_table = QTableWidget(0, 5)
        self.runs_table.setHorizontalHeaderLabels(["Run ID", "Workflow", "Branch", "Status", "Created"])
        self.runs_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        layout.addWidget(self.runs_table, 1)
        return page

    def _navigate(self, index):
        self.stack.setCurrentIndex(index)
        if index == 0:
            self._refresh_dashboard()
        elif index == 1:
            self.refresh_repository_view()
        elif index == 3:
            self._refresh_repo_combos()

    def _message(self, title, text, error=False):
        box = QMessageBox(self)
        box.setWindowTitle(title)
        box.setText(str(text))
        box.setIcon(QMessageBox.Critical if error else QMessageBox.Information)
        box.exec()

    def _log(self, text):
        self.status_label.setText("Ready")
        if hasattr(self, "repo_log"):
            self.repo_log.appendPlainText(str(text))

    def _refresh_accounts(self):
        self.account_picker.blockSignals(True)
        self.account_picker.clear()
        self.account_picker.addItem("No account selected", None)
        self.account_list.clear()
        for account in self.config["accounts"]:
            self.account_picker.addItem(account["label"], account["id"])
            self.account_list.addItem(f'{account["label"]}  ·  @{account["login"]}')
        self.account_picker.blockSignals(False)
        if self.config["accounts"]:
            self.account_picker.setCurrentIndex(1)
            self.current_account = self.config["accounts"][0]
        else:
            self.current_account = None

    def _account_changed(self, index):
        account_id = self.account_picker.currentData()
        self.current_account = next((a for a in self.config["accounts"] if a["id"] == account_id), None)

    def _client(self):
        if not self.current_account:
            raise GitHubError("Select or add a GitHub account first.")
        token = keyring.get_password("GitPilot", self.current_account["id"])
        if not token:
            raise GitHubError("Token is missing from Windows Credential Manager. Re-add this account.")
        return GitHubClient(token)

    def add_account(self):
        dialog = AccountDialog(self)
        if dialog.exec() != QDialog.Accepted:
            return
        label, token = dialog.label.text().strip(), dialog.token.text().strip()
        if not token:
            self._message("Missing token", "Enter a GitHub personal access token.", True); return
        try:
            client = GitHubClient(token)
            user = client.user()
            account_id = user["login"].lower()
            keyring.set_password("GitPilot", account_id, token)
            self.config["accounts"] = [a for a in self.config["accounts"] if a["id"] != account_id]
            self.config["accounts"].append({"id": account_id, "label": label or user["login"], "login": user["login"]})
            save_config(self.config)
            self._refresh_accounts()
            self._message("Account connected", f'Connected as @{user["login"]}.')
        except Exception as exc:
            self._message("Account connection failed", exc, True)

    def remove_account(self):
        idx = self.account_list.currentRow()
        if idx < 0:
            return
        account = self.config["accounts"][idx]
        answer = QMessageBox.question(self, "Remove account", f'Remove @{account["login"]} from GitPilot?')
        if answer != QMessageBox.Yes:
            return
        try:
            keyring.delete_password("GitPilot", account["id"])
        except keyring.errors.PasswordDeleteError:
            pass
        self.config["accounts"].pop(idx)
        save_config(self.config)
        self._refresh_accounts()

    def add_repository(self):
        path = QFileDialog.getExistingDirectory(self, "Select local Git repository")
        if not path:
            return
        if not is_repo(path):
            self._message("Not a Git repository", "The selected folder does not contain a Git repository.", True); return
        if not any(r["path"].lower() == path.lower() for r in self.config["repositories"]):
            self.config["repositories"].append({"path": path, "name": Path(path).name})
            save_config(self.config)
        self._refresh_repositories()
        self._refresh_dashboard()

    def clone_repository(self):
        url, ok = QInputDialog.getText(self, "Clone repository", "GitHub HTTPS or SSH URL:")
        if not ok or not url.strip():
            return
        dest = QFileDialog.getExistingDirectory(self, "Choose parent folder for clone")
        if not dest:
            return
        name = url.rstrip("/").split("/")[-1].removesuffix(".git")
        target = str(Path(dest) / name)
        try:
            clone_repo(url.strip(), target)
            self.config["repositories"].append({"path": target, "name": name})
            save_config(self.config)
            self._refresh_repositories()
            self._message("Clone complete", f"Cloned to {target}")
        except Exception as exc:
            self._message("Clone failed", exc, True)

    def publish_new_folder(self):
        if not self.config["accounts"]:
            self._message("GitHub account required", "Add a GitHub account first.", True); return
        folder = QFileDialog.getExistingDirectory(self, "Select project folder to publish")
        if not folder:
            return
        dialog = PublishDialog(self)
        dialog.account.addItems([a["label"] for a in self.config["accounts"]])
        dialog.name.setText(Path(folder).name)
        if dialog.exec() != QDialog.Accepted:
            return
        account = self.config["accounts"][dialog.account.currentIndex()]
        old = self.current_account
        self.current_account = account
        try:
            client = self._client()
            repo = client.create_repo(dialog.name.text().strip(), dialog.visibility.currentText() == "Private",
                                      dialog.description.text().strip())
            # Prefer SSH URL to avoid storing credentials in a remote URL.
            remote = repo["ssh_url"]
            publish_folder(folder, remote)
            self.config["repositories"].append({"path": folder, "name": Path(folder).name})
            save_config(self.config)
            self._refresh_repositories()
            self._message("Published", f'Repository created: {repo["html_url"]}\n\nLocal project pushed to GitHub.')
        except Exception as exc:
            self._message("Publish failed", exc, True)
        finally:
            self.current_account = old

    def remove_repository(self):
        idx = self.repo_list.currentRow()
        if idx < 0:
            return
        repo = self.config["repositories"][idx]
        if QMessageBox.question(self, "Remove repository", f'Remove {repo["name"]} from GitPilot? (Local files will NOT be deleted)') != QMessageBox.Yes:
            return
        self.config["repositories"].pop(idx)
        save_config(self.config)
        self.current_repo = None
        self._refresh_repositories()
        self._refresh_dashboard()

    def _refresh_repositories(self):
        if not hasattr(self, "repo_list"):
            return
        self.repo_list.clear()
        for repo in self.config["repositories"]:
            self.repo_list.addItem(QListWidgetItem(repo["name"]))
        self._refresh_repo_combos()
        if self.config["repositories"] and self.repo_list.count():
            self.repo_list.setCurrentRow(0)

    def _refresh_repo_combos(self):
        if not hasattr(self, "release_repo"):
            return
        for combo in [self.release_repo, self.actions_repo]:
            combo.clear()
            for repo in self.config["repositories"]:
                combo.addItem(repo["name"], repo["path"])

    def _repo_selected(self, current, previous=None):
        if not current:
            return
        idx = self.repo_list.row(current)
        if idx >= len(self.config["repositories"]):
            return
        self.current_repo = self.config["repositories"][idx]["path"]
        self.refresh_repository_view()

    def refresh_repository_view(self):
        if not self.current_repo or not hasattr(self, "file_table"):
            return
        try:
            info = repo_info(self.current_repo)
            self.repo_title.setText(Path(self.current_repo).name)
            self.repo_meta.setText(f'{self.current_repo}   •   Branch: {info["branch"]}   •   Remote: {info["remote"] or "Not configured"}')
            lines = info["status"].splitlines()
            self.file_table.setRowCount(len(lines))
            for row, line in enumerate(lines):
                status, filename = (line[:2].strip(), line[3:]) if len(line) >= 4 else (line.strip(), "")
                self.file_table.setItem(row, 0, QTableWidgetItem(status))
                self.file_table.setItem(row, 1, QTableWidgetItem(filename))
            self._log(f"Refreshed {self.current_repo}")
            self._refresh_dashboard()
        except Exception as exc:
            self._message("Repository error", exc, True)

    def stage_all(self):
        if not self.current_repo:
            return
        try:
            run_git(self.current_repo, "add", "-A")
            self._log("All changes staged.")
            self.refresh_repository_view()
        except Exception as exc:
            self._message("Stage failed", exc, True)

    def commit_and_push(self):
        if not self.current_repo:
            self._message("Select repository", "Select a repository first.", True); return
        message = self.commit_message.text().strip()
        if not message:
            self._message("Commit message required", "Enter a commit message.", True); return
        try:
            branch = commit_push(self.current_repo, message)
            self.commit_message.clear()
            self._log(f"Committed and pushed to origin/{branch}.")
            self.refresh_repository_view()
            self._message("Push complete", f"Changes pushed to origin/{branch}.")
        except Exception as exc:
            self._message("Commit / push failed", exc, True)

    def _selected_repo_owner(self, combo):
        path = combo.currentData()
        if not path:
            raise GitHubError("Select a repository.")
        remote = repo_info(path)["remote"]
        owner, name = GitHubClient.owner_repo(remote)
        if not owner or not name:
            raise GitHubError("This repository's origin is not a GitHub remote.")
        return path, owner, name

    def create_release(self):
        try:
            path, owner, repo = self._selected_repo_owner(self.release_repo)
            dialog = ReleaseDialog(self)
            if dialog.exec() != QDialog.Accepted:
                return
            tag = dialog.tag.text().strip()
            if not tag:
                raise GitHubError("Release tag is required.")
            client = self._client()
            result = client.create_release(owner, repo, tag, dialog.title.text().strip() or tag,
                                           dialog.notes.toPlainText(), prerelease=dialog.prerelease.isChecked())
            self.release_info.appendPlainText(f'Created {result["html_url"]}')
            self._message("Release created", result["html_url"])
        except Exception as exc:
            self._message("Release failed", exc, True)

    def load_workflow_runs(self):
        try:
            _, owner, repo = self._selected_repo_owner(self.actions_repo)
            runs = self._client().workflow_runs(owner, repo)
            self.runs_table.setRowCount(len(runs))
            for row, run in enumerate(runs):
                values = [str(run["id"]), run["name"], run["head_branch"],
                          f'{run["status"]} / {run.get("conclusion") or "in progress"}',
                          run["created_at"].replace("T", " ").replace("Z", "")]
                for col, value in enumerate(values):
                    self.runs_table.setItem(row, col, QTableWidgetItem(value))
        except Exception as exc:
            self._message("Actions error", exc, True)

    def rerun_selected(self):
        row = self.runs_table.currentRow()
        if row < 0:
            self._message("Select run", "Select a workflow run first.", True); return
        try:
            _, owner, repo = self._selected_repo_owner(self.actions_repo)
            run_id = self.runs_table.item(row, 0).text()
            self._client().rerun_failed(owner, repo, run_id)
            self._message("Workflow", f"Requested rerun for workflow run {run_id}.")
            self.load_workflow_runs()
        except Exception as exc:
            self._message("Rerun failed", exc, True)

    def refresh_all(self):
        self._refresh_accounts()
        self._refresh_repositories()
        self._refresh_dashboard()

    def _refresh_dashboard(self):
        if not hasattr(self, "stat_repos"):
            return
        repos = self.config["repositories"]
        changed = remotes = 0
        for repo in repos:
            try:
                info = repo_info(repo["path"])
                changed += bool(info["status"])
                remotes += bool(info["remote"])
            except Exception:
                pass
        self.stat_repos.value_label.setText(str(len(repos)))
        self.stat_accounts.value_label.setText(str(len(self.config["accounts"])))
        self.stat_changes.value_label.setText(str(changed))
        self.stat_remotes.value_label.setText(str(remotes))

    def closeEvent(self, event):
        save_config(self.config)
        event.accept()
