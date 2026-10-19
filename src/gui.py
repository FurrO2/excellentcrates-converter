from __future__ import annotations

import queue
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from converter import convert


class ConverterApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("ExcellentCrates Converter · v7")
        self.geometry("920x620")
        self.minsize(800, 560)
        self.configure(bg="#f3f5f9")
        self.source = tk.StringVar()
        self.destination = tk.StringVar()
        self.status = tk.StringVar(value="Sélectionnez votre archive ZIP ou le dossier ExcellentCrates.")
        self.results: queue.Queue[tuple[bool, str]] = queue.Queue()
        self._style()
        self._build()

    def _style(self) -> None:
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("TFrame", background="#f3f5f9")
        style.configure("Card.TFrame", background="white")
        style.configure("Title.TLabel", background="#f3f5f9", foreground="#172033", font=("Segoe UI", 23, "bold"))
        style.configure("Subtitle.TLabel", background="#f3f5f9", foreground="#667085", font=("Segoe UI", 10))
        style.configure("CardTitle.TLabel", background="white", foreground="#202b3c", font=("Segoe UI", 13, "bold"))
        style.configure("Body.TLabel", background="white", foreground="#586174", font=("Segoe UI", 10))
        style.configure("Primary.TButton", font=("Segoe UI", 11, "bold"), padding=(20, 12))
        style.map("Primary.TButton", background=[("!disabled", "#5b5be8"), ("disabled", "#a4a4d5")], foreground=[("!disabled", "white")])

    def _build(self) -> None:
        outer = ttk.Frame(self, padding=(30, 24, 30, 20))
        outer.pack(fill="both", expand=True)
        ttk.Label(outer, text="ExcellentCrates Converter", style="Title.TLabel").pack(anchor="w")
        ttk.Label(outer, text="Convertissez vos anciennes données vers le format v7 en quelques clics.", style="Subtitle.TLabel").pack(anchor="w", pady=(4, 22))

        columns = ttk.Frame(outer)
        columns.pack(fill="both", expand=True)
        columns.columnconfigure(0, weight=1, uniform="cards")
        columns.columnconfigure(1, weight=1, uniform="cards")
        columns.rowconfigure(0, weight=1)

        left = ttk.Frame(columns, style="Card.TFrame", padding=22)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 9))
        ttk.Label(left, text="1 · Anciennes données", style="CardTitle.TLabel").pack(anchor="w")
        ttk.Label(left, text="Choisissez le ZIP complet du plugin ou son dossier racine contenant crates/ et keys/.", style="Body.TLabel", wraplength=340, justify="left").pack(anchor="w", pady=(7, 17))
        self.source_box = tk.Label(left, text="Aucune source sélectionnée", bg="#f7f8fc", fg="#667085", font=("Segoe UI", 10), wraplength=330, justify="left", anchor="nw", padx=12, pady=12, height=5, relief="solid", bd=1, highlightthickness=0)
        self.source_box.pack(fill="x")
        ttk.Button(left, text="Choisir un fichier ZIP…", command=self._choose_zip).pack(fill="x", pady=(12, 7))
        ttk.Button(left, text="Choisir un dossier…", command=self._choose_folder).pack(fill="x")

        right = ttk.Frame(columns, style="Card.TFrame", padding=22)
        right.grid(row=0, column=1, sticky="nsew", padx=(9, 0))
        ttk.Label(right, text="2 · Résultat v7", style="CardTitle.TLabel").pack(anchor="w")
        ttk.Label(right, text="Le convertisseur crée un nouveau dossier sans écraser de fichiers existants.", style="Body.TLabel", wraplength=340, justify="left").pack(anchor="w", pady=(7, 12))
        ttk.Label(right, text="Dossier de destination", style="Body.TLabel").pack(anchor="w")
        destination_row = ttk.Frame(right, style="Card.TFrame")
        destination_row.pack(fill="x", pady=(5, 14))
        self.destination_entry = ttk.Entry(destination_row, textvariable=self.destination)
        self.destination_entry.pack(side="left", fill="x", expand=True, ipady=5)
        ttk.Button(destination_row, text="Parcourir…", command=self._choose_destination).pack(side="left", padx=(7, 0))

        ttk.Separator(right).pack(fill="x", pady=(2, 13))
        ttk.Label(right, text="Où installer le résultat ?", style="CardTitle.TLabel", font=("Segoe UI", 11, "bold")).pack(anchor="w")
        notice = ("Après la conversion, sauvegardez votre dossier de plugin v7. "
                  "Copiez le contenu du dossier objects généré dans le dossier objects de votre installation ExcellentCrates v7 "
                  "(souvent plugins/ExcellentCrates/objects), en conservant la structure des sous-dossiers. "
                  "Ne copiez pas manifest.json ni conversion-report.json dans objects. Redémarrez le serveur et vérifiez les caisses en jeu.")
        ttk.Label(right, text=notice, style="Body.TLabel", wraplength=340, justify="left").pack(anchor="w", pady=(7, 0))

        footer = ttk.Frame(outer)
        footer.pack(fill="x", pady=(17, 0))
        self.convert_button = ttk.Button(footer, text="Convertir vers v7", style="Primary.TButton", command=self._start)
        self.convert_button.pack(side="right")
        ttk.Label(footer, textvariable=self.status, style="Subtitle.TLabel", wraplength=520).pack(side="left", fill="x", expand=True, padx=(0, 18))

    def _choose_zip(self) -> None:
        path = filedialog.askopenfilename(title="Choisir l'archive ExcellentCrates", filetypes=[("Archives ZIP", "*.zip"), ("Tous les fichiers", "*.*")])
        if path:
            self._set_source(Path(path))

    def _choose_folder(self) -> None:
        path = filedialog.askdirectory(title="Choisir le dossier ExcellentCrates legacy")
        if path:
            self._set_source(Path(path))

    def _set_source(self, path: Path) -> None:
        self.source.set(str(path))
        self.source_box.configure(text=str(path), fg="#202b3c")
        default = path.parent / "excellentcrates [converted]"
        suffix = 2
        while default.exists() and any(default.iterdir()):
            default = path.parent / f"excellentcrates [converted {suffix}]"
            suffix += 1
        self.destination.set(str(default))

    def _choose_destination(self) -> None:
        path = filedialog.askdirectory(title="Choisir le dossier parent du résultat")
        if path:
            current = Path(self.destination.get()).name or "excellentcrates [converted]"
            self.destination.set(str(Path(path) / current))

    def _start(self) -> None:
        source = Path(self.source.get()) if self.source.get() else None
        destination = Path(self.destination.get()) if self.destination.get() else None
        if source is None or not source.exists():
            messagebox.showerror("Source manquante", "Choisissez un fichier ZIP ou un dossier ExcellentCrates valide.")
            return
        if destination is None:
            messagebox.showerror("Destination manquante", "Choisissez le dossier de sortie.")
            return
        if destination.exists() and (not destination.is_dir() or any(destination.iterdir())):
            messagebox.showerror("Dossier déjà utilisé", "Le dossier de destination existe et n'est pas vide. Choisissez un nouveau dossier vide.")
            return
        self.convert_button.configure(state="disabled")
        self.status.set("Conversion en cours…")
        threading.Thread(target=self._convert_worker, args=(source, destination), daemon=True).start()
        self.after(100, self._poll)

    def _convert_worker(self, source: Path, destination: Path) -> None:
        try:
            result = convert(source, destination)
            summary = (f"Conversion terminée : {result['crates_converted']} caisses, "
                       f"{result['keys_converted']} clés.\n\n"
                       f"Résultat : {destination}\n\n"
                       "Consultez conversion-report.json pour les adaptations à vérifier.")
            self.results.put((True, summary))
        except Exception as exc:
            self.results.put((False, str(exc)))

    def _poll(self) -> None:
        try:
            success, message = self.results.get_nowait()
        except queue.Empty:
            self.after(100, self._poll)
            return
        self.convert_button.configure(state="normal")
        self.status.set("Conversion terminée." if success else "La conversion a rencontré une erreur.")
        if success:
            messagebox.showinfo("Conversion terminée", message)
        else:
            messagebox.showerror("Conversion impossible", message)


if __name__ == "__main__":
    ConverterApp().mainloop()
