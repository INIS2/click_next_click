import json
import threading
from copy import deepcopy
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from playwright.sync_api import Error, TimeoutError as PlaywrightTimeoutError, sync_playwright


APP_DIR = Path(__file__).resolve().parent
DATA_DIR = APP_DIR / "data"

ACTIONS = ["open", "goto", "check", "wait", "click", "fill", "close"]
SELECTOR_MODES = ["none", "css", "id", "class", "text", "placeholder", "label", "role"]

DEFAULT_WORKFLOW = {
    "settings": {
        "headless": False,
        "timeout_ms": 10000,
        "start_url": "",
    },
    "steps": [],
}


class BrowserRuntime:
    def __init__(self):
        self.playwright = None
        self.browser = None
        self.context = None
        self.page = None

    def open(self, headless: bool):
        if self.page:
            return
        self.playwright = sync_playwright().start()
        self.browser = self.playwright.chromium.launch(headless=headless)
        self.context = self.browser.new_context()
        self.page = self.context.new_page()

    def close(self):
        errors = []
        for obj_name in ("page", "context", "browser", "playwright"):
            obj = getattr(self, obj_name)
            if not obj:
                continue
            try:
                obj.close() if obj_name != "playwright" else obj.stop()
            except Exception as exc:  # noqa: BLE001
                errors.append(f"{obj_name}: {exc}")
            finally:
                setattr(self, obj_name, None)
        return errors


class ClickNextClickApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("click_next_click")
        self.root.geometry("1180x760")

        self.workflow = deepcopy(DEFAULT_WORKFLOW)
        self.selected_index = None

        self.headless_var = tk.BooleanVar(value=False)
        self.timeout_var = tk.StringVar(value="10000")
        self.start_url_var = tk.StringVar(value="")

        self.action_var = tk.StringVar(value="open")
        self.selector_mode_var = tk.StringVar(value="none")
        self.selector_var = tk.StringVar(value="")
        self.value_var = tk.StringVar(value="")
        self.note_var = tk.StringVar(value="")
        self.required_var = tk.BooleanVar(value=True)

        self._build_ui()
        self.refresh_tree()
        self.load_default_sample()

    def _build_ui(self):
        outer = ttk.Frame(self.root, padding=12)
        outer.pack(fill="both", expand=True)

        settings = ttk.LabelFrame(outer, text="Settings", padding=10)
        settings.pack(fill="x")

        ttk.Checkbutton(settings, text="Headless", variable=self.headless_var).grid(row=0, column=0, sticky="w")
        ttk.Label(settings, text="Timeout(ms)").grid(row=0, column=1, sticky="w", padx=(12, 4))
        ttk.Entry(settings, textvariable=self.timeout_var, width=12).grid(row=0, column=2, sticky="w")
        ttk.Label(settings, text="Start URL").grid(row=0, column=3, sticky="w", padx=(12, 4))
        ttk.Entry(settings, textvariable=self.start_url_var, width=70).grid(row=0, column=4, sticky="ew")
        settings.columnconfigure(4, weight=1)

        controls = ttk.Frame(outer, padding=(0, 10, 0, 10))
        controls.pack(fill="x")

        ttk.Button(controls, text="New", command=self.new_workflow).pack(side="left")
        ttk.Button(controls, text="Load JSON", command=self.load_workflow).pack(side="left", padx=(6, 0))
        ttk.Button(controls, text="Save JSON", command=self.save_workflow).pack(side="left", padx=(6, 0))
        ttk.Button(controls, text="Run", command=self.run_workflow).pack(side="left", padx=(20, 0))

        middle = ttk.Frame(outer)
        middle.pack(fill="both", expand=True)

        left = ttk.Frame(middle)
        left.pack(side="left", fill="both", expand=True)

        columns = ("idx", "action", "selector_mode", "selector", "value", "required", "note")
        self.tree = ttk.Treeview(left, columns=columns, show="headings", height=16)
        for col, width in (
            ("idx", 60),
            ("action", 90),
            ("selector_mode", 110),
            ("selector", 220),
            ("value", 240),
            ("required", 80),
            ("note", 260),
        ):
            self.tree.heading(col, text=col)
            self.tree.column(col, width=width, anchor="w")
        self.tree.pack(side="left", fill="both", expand=True)
        self.tree.bind("<<TreeviewSelect>>", self.on_tree_select)

        scrollbar = ttk.Scrollbar(left, orient="vertical", command=self.tree.yview)
        scrollbar.pack(side="right", fill="y")
        self.tree.configure(yscrollcommand=scrollbar.set)

        editor = ttk.LabelFrame(middle, text="Step Editor", padding=10)
        editor.pack(side="left", fill="y", padx=(12, 0))

        ttk.Label(editor, text="Action").grid(row=0, column=0, sticky="w")
        ttk.Combobox(editor, textvariable=self.action_var, values=ACTIONS, state="readonly", width=18).grid(
            row=0, column=1, sticky="ew", pady=(0, 8)
        )

        ttk.Label(editor, text="Selector mode").grid(row=1, column=0, sticky="w")
        ttk.Combobox(
            editor,
            textvariable=self.selector_mode_var,
            values=SELECTOR_MODES,
            state="readonly",
            width=18,
        ).grid(row=1, column=1, sticky="ew", pady=(0, 8))

        ttk.Label(editor, text="Selector").grid(row=2, column=0, sticky="w")
        ttk.Entry(editor, textvariable=self.selector_var, width=32).grid(row=2, column=1, sticky="ew", pady=(0, 8))

        ttk.Label(editor, text="Value").grid(row=3, column=0, sticky="w")
        ttk.Entry(editor, textvariable=self.value_var, width=32).grid(row=3, column=1, sticky="ew", pady=(0, 8))

        ttk.Label(editor, text="Note").grid(row=4, column=0, sticky="w")
        ttk.Entry(editor, textvariable=self.note_var, width=32).grid(row=4, column=1, sticky="ew", pady=(0, 8))

        ttk.Checkbutton(editor, text="Required", variable=self.required_var).grid(row=5, column=1, sticky="w", pady=(0, 10))

        ttk.Button(editor, text="Add Step", command=self.add_step).grid(row=6, column=0, sticky="ew")
        ttk.Button(editor, text="Update Step", command=self.update_step).grid(row=6, column=1, sticky="ew", pady=(0, 6))
        ttk.Button(editor, text="Delete Step", command=self.delete_step).grid(row=7, column=0, sticky="ew")
        ttk.Button(editor, text="Move Up", command=lambda: self.move_step(-1)).grid(row=7, column=1, sticky="ew", pady=(0, 6))
        ttk.Button(editor, text="Move Down", command=lambda: self.move_step(1)).grid(row=8, column=1, sticky="ew")
        ttk.Button(editor, text="Clear Form", command=self.clear_form).grid(row=8, column=0, sticky="ew")
        editor.columnconfigure(1, weight=1)

        log_frame = ttk.LabelFrame(outer, text="Execution Log", padding=10)
        log_frame.pack(fill="both", expand=True, pady=(12, 0))

        self.log_text = tk.Text(log_frame, height=12, wrap="word")
        self.log_text.pack(fill="both", expand=True)

    def sync_settings_to_model(self):
        self.workflow["settings"]["headless"] = self.headless_var.get()
        try:
            timeout_ms = int(self.timeout_var.get().strip())
        except ValueError as exc:
            raise ValueError("Timeout must be an integer.") from exc
        self.workflow["settings"]["timeout_ms"] = timeout_ms
        self.workflow["settings"]["start_url"] = self.start_url_var.get().strip()

    def sync_settings_from_model(self):
        settings = self.workflow["settings"]
        self.headless_var.set(settings.get("headless", False))
        self.timeout_var.set(str(settings.get("timeout_ms", 10000)))
        self.start_url_var.set(settings.get("start_url", ""))

    def read_form(self):
        action = self.action_var.get().strip()
        selector_mode = self.selector_mode_var.get().strip() or "none"
        selector = self.selector_var.get().strip()
        value = self.value_var.get().strip()
        note = self.note_var.get().strip()
        required = self.required_var.get()

        if action not in ACTIONS:
            raise ValueError("Choose a valid action.")
        if selector_mode not in SELECTOR_MODES:
            raise ValueError("Choose a valid selector mode.")
        if action in {"click", "fill", "check", "wait"} and selector_mode == "none":
            raise ValueError(f"{action} requires a selector mode.")
        if action in {"goto"} and not value:
            raise ValueError("goto requires a URL in value.")
        if action == "fill" and not value:
            raise ValueError("fill requires input text in value.")
        if action == "role" and selector_mode != "role":
            raise ValueError("Role action is not supported.")

        return {
            "action": action,
            "selector_mode": selector_mode,
            "selector": selector,
            "value": value,
            "note": note,
            "required": required,
        }

    def add_step(self):
        try:
            self.sync_settings_to_model()
            step = self.read_form()
        except ValueError as exc:
            messagebox.showerror("Invalid step", str(exc))
            return
        self.workflow["steps"].append(step)
        self.refresh_tree()
        self.clear_form()

    def update_step(self):
        if self.selected_index is None:
            messagebox.showinfo("No selection", "Select a step first.")
            return
        try:
            self.sync_settings_to_model()
            self.workflow["steps"][self.selected_index] = self.read_form()
        except ValueError as exc:
            messagebox.showerror("Invalid step", str(exc))
            return
        self.refresh_tree()

    def delete_step(self):
        if self.selected_index is None:
            messagebox.showinfo("No selection", "Select a step first.")
            return
        del self.workflow["steps"][self.selected_index]
        self.selected_index = None
        self.refresh_tree()
        self.clear_form()

    def move_step(self, offset: int):
        if self.selected_index is None:
            messagebox.showinfo("No selection", "Select a step first.")
            return
        new_index = self.selected_index + offset
        if new_index < 0 or new_index >= len(self.workflow["steps"]):
            return
        steps = self.workflow["steps"]
        steps[self.selected_index], steps[new_index] = steps[new_index], steps[self.selected_index]
        self.selected_index = new_index
        self.refresh_tree()
        self.tree.selection_set(str(self.selected_index))

    def clear_form(self):
        self.action_var.set("open")
        self.selector_mode_var.set("none")
        self.selector_var.set("")
        self.value_var.set("")
        self.note_var.set("")
        self.required_var.set(True)
        self.tree.selection_remove(*self.tree.selection())
        self.selected_index = None

    def refresh_tree(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        for idx, step in enumerate(self.workflow["steps"]):
            self.tree.insert(
                "",
                "end",
                iid=str(idx),
                values=(
                    idx + 1,
                    step.get("action", ""),
                    step.get("selector_mode", ""),
                    step.get("selector", ""),
                    step.get("value", ""),
                    "Y" if step.get("required", True) else "N",
                    step.get("note", ""),
                ),
            )

    def on_tree_select(self, _event=None):
        selection = self.tree.selection()
        if not selection:
            return
        self.selected_index = int(selection[0])
        step = self.workflow["steps"][self.selected_index]
        self.action_var.set(step.get("action", "open"))
        self.selector_mode_var.set(step.get("selector_mode", "none"))
        self.selector_var.set(step.get("selector", ""))
        self.value_var.set(step.get("value", ""))
        self.note_var.set(step.get("note", ""))
        self.required_var.set(step.get("required", True))

    def new_workflow(self):
        self.workflow = deepcopy(DEFAULT_WORKFLOW)
        self.sync_settings_from_model()
        self.refresh_tree()
        self.clear_form()
        self.log("Started a new workflow.")

    def default_json_path(self):
        DATA_DIR.mkdir(exist_ok=True)
        return DATA_DIR / "action3.json"

    def load_default_sample(self):
        sample_path = self.default_json_path()
        if sample_path.exists():
            self.load_workflow_from_path(sample_path, silent=True)

    def load_workflow(self):
        DATA_DIR.mkdir(exist_ok=True)
        path = filedialog.askopenfilename(
            title="Load workflow JSON",
            initialdir=DATA_DIR,
            filetypes=[("JSON files", "*.json")],
        )
        if not path:
            return
        self.load_workflow_from_path(Path(path))

    def load_workflow_from_path(self, path: Path, silent: bool = False):
        try:
            with path.open("r", encoding="utf-8") as file:
                data = json.load(file)
            self.validate_workflow(data)
            self.workflow = data
            self.sync_settings_from_model()
            self.refresh_tree()
            self.clear_form()
            if not silent:
                self.log(f"Loaded workflow: {path.name}")
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror("Load failed", str(exc))

    def save_workflow(self):
        try:
            self.sync_settings_to_model()
        except ValueError as exc:
            messagebox.showerror("Invalid settings", str(exc))
            return
        DATA_DIR.mkdir(exist_ok=True)
        path = filedialog.asksaveasfilename(
            title="Save workflow JSON",
            initialdir=DATA_DIR,
            initialfile="action3.json",
            defaultextension=".json",
            filetypes=[("JSON files", "*.json")],
        )
        if not path:
            return
        with Path(path).open("w", encoding="utf-8") as file:
            json.dump(self.workflow, file, indent=2, ensure_ascii=False)
        self.log(f"Saved workflow: {Path(path).name}")

    def validate_workflow(self, data):
        if not isinstance(data, dict):
            raise ValueError("Workflow JSON must be an object.")
        if "settings" not in data or "steps" not in data:
            raise ValueError("Workflow JSON must contain settings and steps.")
        if not isinstance(data["steps"], list):
            raise ValueError("steps must be a list.")
        settings = data["settings"]
        if not isinstance(settings.get("headless", False), bool):
            raise ValueError("settings.headless must be a boolean.")
        if not isinstance(settings.get("timeout_ms", 10000), int):
            raise ValueError("settings.timeout_ms must be an integer.")
        if not isinstance(settings.get("start_url", ""), str):
            raise ValueError("settings.start_url must be a string.")
        for step in data["steps"]:
            if step.get("action") not in ACTIONS:
                raise ValueError(f"Unknown action: {step.get('action')}")
            if step.get("selector_mode", "none") not in SELECTOR_MODES:
                raise ValueError(f"Unknown selector_mode: {step.get('selector_mode')}")

    def log(self, message: str):
        def append():
            self.log_text.insert("end", message + "\n")
            self.log_text.see("end")

        self.root.after(0, append)

    def run_workflow(self):
        try:
            self.sync_settings_to_model()
        except ValueError as exc:
            messagebox.showerror("Invalid settings", str(exc))
            return
        if not self.workflow["steps"]:
            messagebox.showinfo("No steps", "Add at least one step first.")
            return
        self.log("Running workflow...")
        thread = threading.Thread(target=self._run_workflow_worker, daemon=True)
        thread.start()

    def _run_workflow_worker(self):
        runtime = BrowserRuntime()
        settings = self.workflow["settings"]
        timeout_ms = settings["timeout_ms"]

        try:
            for index, step in enumerate(self.workflow["steps"], start=1):
                self.log(f"[{index}] {step['action']} started")
                self.execute_step(step, runtime, settings, timeout_ms)
                self.log(f"[{index}] {step['action']} completed")
        except Exception as exc:  # noqa: BLE001
            self.log(f"Workflow stopped: {exc}")
        finally:
            close_errors = runtime.close()
            for err in close_errors:
                self.log(f"Close warning: {err}")
            self.log("Workflow finished.")

    def execute_step(self, step, runtime: BrowserRuntime, settings, timeout_ms: int):
        action = step["action"]
        required = step.get("required", True)

        try:
            if action == "open":
                runtime.open(settings["headless"])
                url = step.get("value") or settings.get("start_url", "")
                if url:
                    runtime.page.goto(url, wait_until="load", timeout=timeout_ms)
                return

            if action == "close":
                close_errors = runtime.close()
                for err in close_errors:
                    self.log(f"Close warning: {err}")
                return

            if runtime.page is None:
                raise RuntimeError("Browser is not open. Add an open step first.")

            if action == "goto":
                runtime.page.goto(step.get("value", ""), wait_until="load", timeout=timeout_ms)
                return

            locator = self.build_locator(runtime.page, step)

            if action == "check":
                if locator.count() < 1:
                    raise RuntimeError(f"Element not found: {step.get('selector')}")
                return

            if action == "wait":
                locator.first.wait_for(state="visible", timeout=timeout_ms)
                return

            if action == "click":
                locator.first.click(timeout=timeout_ms)
                return

            if action == "fill":
                locator.first.fill(step.get("value", ""), timeout=timeout_ms)
                return

            raise RuntimeError(f"Unsupported action: {action}")
        except (PlaywrightTimeoutError, Error, RuntimeError) as exc:
            if required:
                raise
            self.log(f"Optional step skipped after error: {exc}")

    def build_locator(self, page, step):
        mode = step.get("selector_mode", "none")
        selector = step.get("selector", "")
        value = step.get("value", "")

        if mode == "css":
            return page.locator(selector)
        if mode == "id":
            return page.locator(f"#{selector}")
        if mode == "class":
            return page.locator(f".{selector}")
        if mode == "text":
            return page.get_by_text(selector)
        if mode == "placeholder":
            return page.get_by_placeholder(selector)
        if mode == "label":
            return page.get_by_label(selector)
        if mode == "role":
            role_name = selector.strip()
            accessible_name = value.strip() or None
            return page.get_by_role(role_name, name=accessible_name)
        raise RuntimeError(f"Unsupported selector mode: {mode}")


def main():
    DATA_DIR.mkdir(exist_ok=True)
    root = tk.Tk()
    app = ClickNextClickApp(root)
    app.log("Ready.")
    root.mainloop()


if __name__ == "__main__":
    main()
