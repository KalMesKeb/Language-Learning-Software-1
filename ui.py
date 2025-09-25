# ui.py
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import json
import os
from db import save_user, get_user, update_profile, save_progress, load_progress, cache_lessons, load_cached_lesson
from utils import hash_password, split_words, escape
from tts_engine import TTSEngine
from nlp_engine import tokenize_and_tag
from exercises import generate_matching, generate_fill_blank
from models import Lesson, Sentence
from typing import List

LESSONS_FILE = os.path.join("lessons", "lessons.json")

class AppUI:
    def __init__(self, root):
        self.root = root
        root.title("Natural Language Learning — English for Amharic Speakers")
        root.geometry("1000x700")
        self.current_user = None
        self.current_user_id = None
        self.tts = TTSEngine()
        self.lessons = self.load_lessons()
        self.progress = {}
        self.selected_lesson = None
        self.setup_ui()

    def load_lessons(self):
        if not os.path.exists(LESSONS_FILE):
            return []
        with open(LESSONS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        lessons = []
        for l in data.get("lessons", []):
            sentences = []
            for s in l.get("sentences", []):
                sentences.append(Sentence(id=s["id"], english=s["english"], amharic=s["amharic"], alignment=s.get("alignment", []), notes=s.get("notes", "")))
            lessons.append(Lesson(id=l["id"], title=l["title"], level=l.get("level", "Beginner"), sentences=sentences, vocabulary=l.get("vocabulary", [])))
            # cache to DB (encrypted)
            cache_lessons(l["id"], l)
        return lessons

    def setup_ui(self):
        # top frame: login/register or profile
        top = ttk.Frame(self.root)
        top.pack(side=tk.TOP, fill=tk.X, padx=8, pady=8)

        self.user_label = ttk.Label(top, text="Not logged in")
        self.user_label.pack(side=tk.LEFT)

        ttk.Button(top, text="Login", command=self.login_dialog).pack(side=tk.RIGHT, padx=4)
        ttk.Button(top, text="Register", command=self.register_dialog).pack(side=tk.RIGHT, padx=4)
        ttk.Button(top, text="Settings", command=self.settings_dialog).pack(side=tk.RIGHT, padx=4)

        # main panes
        main = ttk.Panedwindow(self.root, orient=tk.HORIZONTAL)
        main.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)

        # left: lesson list
        left_frame = ttk.Frame(main, width=300)
        main.add(left_frame, weight=1)
        ttk.Label(left_frame, text="Lessons").pack(anchor=tk.W)
        self.lesson_list = tk.Listbox(left_frame)
        self.lesson_list.pack(fill=tk.BOTH, expand=True)
        for l in self.lessons:
            self.lesson_list.insert(tk.END, f"{l.id} - {l.title} ({l.level})")
        self.lesson_list.bind("<<ListboxSelect>>", self.on_lesson_select)

        # center: lesson details / DIT
        center_frame = ttk.Frame(main)
        main.add(center_frame, weight=3)
        header = ttk.Frame(center_frame)
        header.pack(fill=tk.X)
        self.lesson_title = ttk.Label(header, text="Select a lesson", font=("Helvetica", 16))
        self.lesson_title.pack(side=tk.LEFT, padx=4)
        ttk.Button(header, text="Play Sentence (EN)", command=lambda: self.play_current_sentence('en')).pack(side=tk.RIGHT, padx=4)
        ttk.Button(header, text="Play Sentence (AM)", command=lambda: self.play_current_sentence('am')).pack(side=tk.RIGHT, padx=4)
        self.sentence_nav = ttk.Frame(center_frame)
        self.sentence_nav.pack(fill=tk.X, pady=6)
        ttk.Button(self.sentence_nav, text="Previous", command=self.prev_sentence).pack(side=tk.LEFT)
        ttk.Button(self.sentence_nav, text="Next", command=self.next_sentence).pack(side=tk.LEFT)

        # DIT area
        self.dit_frame = ttk.Frame(center_frame)
        self.dit_frame.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)
        self.eng_text = tk.Text(self.dit_frame, height=4, wrap=tk.WORD)
        self.eng_text.pack(fill=tk.X)
        self.amh_text = tk.Text(self.dit_frame, height=4, wrap=tk.WORD)
        self.amh_text.pack(fill=tk.X)
        self.eng_text.config(state=tk.DISABLED)
        self.amh_text.config(state=tk.DISABLED)

        # bottom: exercises & vocab
        bottom = ttk.Frame(self.root)
        bottom.pack(side=tk.BOTTOM, fill=tk.X, padx=8, pady=8)
        ttk.Button(bottom, text="Vocabulary Builder", command=self.open_vocab_builder).pack(side=tk.LEFT, padx=4)
        ttk.Button(bottom, text="Exercises", command=self.open_exercises).pack(side=tk.LEFT, padx=4)
        self.progress_label = ttk.Label(bottom, text="Progress: N/A")
        self.progress_label.pack(side=tk.RIGHT)

        # state
        self.lesson_index = None
        self.sentence_index = 0

    # --- auth dialogs ---
    def register_dialog(self):
        d = tk.Toplevel(self.root)
        d.title("Register")
        ttk.Label(d, text="Username:").grid(row=0, column=0, sticky=tk.W, pady=4)
        uname = ttk.Entry(d)
        uname.grid(row=0, column=1, pady=4)
        ttk.Label(d, text="Password:").grid(row=1, column=0, sticky=tk.W, pady=4)
        pwd = ttk.Entry(d, show="*")
        pwd.grid(row=1, column=1, pady=4)
        def do_register():
            u = uname.get().strip()
            p = pwd.get().strip()
            if not u or not p:
                messagebox.showerror("Error", "Please enter username and password")
                return
            hid = hash_password(p)
            uid = save_user(u, hid, {"prefs": {"tts_rate": self.tts.rate}})
            if not uid:
                messagebox.showerror("Error", "Username already exists")
            else:
                messagebox.showinfo("Registered", "Account created. Please login.")
                d.destroy()
        ttk.Button(d, text="Register", command=do_register).grid(row=2, column=0, columnspan=2, pady=8)

    def login_dialog(self):
        d = tk.Toplevel(self.root)
        d.title("Login")
        ttk.Label(d, text="Username:").grid(row=0, column=0, sticky=tk.W, pady=4)
        uname = ttk.Entry(d)
        uname.grid(row=0, column=1, pady=4)
        ttk.Label(d, text="Password:").grid(row=1, column=0, sticky=tk.W, pady=4)
        pwd = ttk.Entry(d, show="*")
        pwd.grid(row=1, column=1, pady=4)
        def do_login():
            u = uname.get().strip()
            p = pwd.get().strip()
            if not u or not p:
                messagebox.showerror("Error", "Please enter username and password")
                return
            info = get_user(u)
            if not info or info["password"] != hash_password(p):
                messagebox.showerror("Error", "Invalid username or password")
                return
            self.current_user = info["username"]
            self.current_user_id = info["id"]
            self.user_label.config(text=f"Logged in: {self.current_user}")
            # load progress
            self.progress = load_progress(self.current_user_id) or {}
            self.update_progress_ui()
            d.destroy()
        ttk.Button(d, text="Login", command=do_login).grid(row=2, column=0, columnspan=2, pady=8)

    def settings_dialog(self):
        if not self.current_user:
            messagebox.showinfo("Not logged in", "Login to access settings.")
            return
        d = tk.Toplevel(self.root)
        d.title("Settings")
        ttk.Label(d, text="TTS Rate (words per minute):").pack(anchor=tk.W, padx=6, pady=6)
        sp = ttk.Scale(d, from_=80, to=300, orient=tk.HORIZONTAL)
        sp.set(self.tts.rate)
        sp.pack(fill=tk.X, padx=6)
        def save():
            self.tts.set_rate(int(sp.get()))
            # save to profile
            info = get_user(self.current_user)
            if info:
                prof = info.get("profile", {})
                prof["prefs"] = prof.get("prefs", {})
                prof["prefs"]["tts_rate"] = self.tts.rate
                update_profile(info["id"], prof)
                messagebox.showinfo("Saved", "Settings saved")
            d.destroy()
        ttk.Button(d, text="Save", command=save).pack(pady=6)

    # --- lesson navigation & DIT display ---
    def on_lesson_select(self, event):
        idx = self.lesson_list.curselection()
        if not idx:
            return
        i = idx[0]
        self.lesson_index = i
        self.selected_lesson = self.lessons[i]
        self.sentence_index = 0
        self.lesson_title.config(text=f"{self.selected_lesson.title} ({self.selected_lesson.level})")
        self.show_sentence()

    def show_sentence(self):
        if not self.selected_lesson:
            return
        if not (0 <= self.sentence_index < len(self.selected_lesson.sentences)):
            return
        s = self.selected_lesson.sentences[self.sentence_index]
        # show english and amharic with word-level clickable spans
        self.eng_text.config(state=tk.NORMAL)
        self.amh_text.config(state=tk.NORMAL)
        self.eng_text.delete("1.0", tk.END)
        self.amh_text.delete("1.0", tk.END)

        # insert english tokens and tag them for click
        eng_words = split_words(s.english)
        for i, w in enumerate(eng_words):
            tag = f"eng_{i}"
            start_index = self.eng_text.index(tk.INSERT)
            self.eng_text.insert(tk.END, w + " ")
            end_index = self.eng_text.index(tk.INSERT)
            self.eng_text.tag_add(tag, start_index, end_index)
            self.eng_text.tag_bind(tag, "<Button-1>", lambda e, idx=i: self.on_eng_click(idx))
            self.eng_text.tag_config(tag, underline=True)
        # amharic: for alignment show words in same order as provided alignment if present
        # If alignment present, show aligned amh tokens in order
        if s.alignment:
            for i, pair in enumerate(s.alignment):
                w = pair.get("amh", "")
                tag = f"amh_{i}"
                start_index = self.amh_text.index(tk.INSERT)
                self.amh_text.insert(tk.END, w + " ")
                end_index = self.amh_text.index(tk.INSERT)
                self.amh_text.tag_add(tag, start_index, end_index)
                self.amh_text.tag_bind(tag, "<Button-1>", lambda e, idx=i: self.on_amh_click(idx))
                self.amh_text.tag_config(tag, underline=True)
        else:
            amh_words = split_words(s.amharic)
            for i, w in enumerate(amh_words):
                start_index = self.amh_text.index(tk.INSERT)
                self.amh_text.insert(tk.END, w + " ")
                end_index = self.amh_text.index(tk.INSERT)

        self.eng_text.config(state=tk.DISABLED)
        self.amh_text.config(state=tk.DISABLED)

        # show grammar hints (POS tags) below
        tags = tokenize_and_tag(s.english)
        grammar_hint = " | ".join([f"{t}:{p}" for t,p in tags])
        # display in a small label
        if hasattr(self, "grammar_label"):
            self.grammar_label.config(text=grammar_hint)
        else:
            self.grammar_label = ttk.Label(self.dit_frame, text=grammar_hint, foreground="gray")
            self.grammar_label.pack(anchor=tk.W, pady=4)

        # update progress tracker
        self.update_progress_for_sentence(self.selected_lesson.id, s.id)

    def on_eng_click(self, idx):
        # display translation and grammar for the clicked english word by index
        s = self.selected_lesson.sentences[self.sentence_index]
        if idx < len(s.alignment):
            pair = s.alignment[idx]
            eng = pair.get("eng", "")
            amh = pair.get("amh", "")
            # show a small popup with TTS buttons
            d = tk.Toplevel(self.root)
            d.title(f"Word: {eng}")
            ttk.Label(d, text=f"English: {eng}").pack(anchor=tk.W, padx=6, pady=4)
            ttk.Label(d, text=f"Amharic: {amh}").pack(anchor=tk.W, padx=6, pady=4)
            # example grammatical note
            ttk.Label(d, text=f"Note: {s.notes or '—'}").pack(anchor=tk.W, padx=6, pady=4)
            ttk.Button(d, text="Play English", command=lambda: self.tts.say_async(eng)).pack(side=tk.LEFT, padx=6, pady=6)
            ttk.Button(d, text="Play Amharic", command=lambda: self.tts.say_async(amh)).pack(side=tk.LEFT, padx=6, pady=6)
        else:
            messagebox.showinfo("Info", "No aligned translation for this word in lesson data.")

    def on_amh_click(self, idx):
        s = self.selected_lesson.sentences[self.sentence_index]
        if idx < len(s.alignment):
            pair = s.alignment[idx]
            eng = pair.get("eng", "")
            amh = pair.get("amh", "")
            messagebox.showinfo("Translation", f"{amh}  —  {eng}")

    def prev_sentence(self):
        if self.selected_lesson and self.sentence_index > 0:
            self.sentence_index -= 1
            self.show_sentence()

    def next_sentence(self):
        if self.selected_lesson and self.sentence_index < len(self.selected_lesson.sentences)-1:
            self.sentence_index += 1
            self.show_sentence()

    def play_current_sentence(self, lang='en'):
        if not self.selected_lesson:
            return
        s = self.selected_lesson.sentences[self.sentence_index]
        if lang == 'en':
            self.tts.say_async(s.english)
        else:
            # amharic may or may not have a dedicated voice; attempt to use system voice for Amharic
            # Try set a voice with 'amh' or 'amharic' in its name; else fallback
            chosen = None
            for vid, v in self.tts.voice_map.items():
                lname = str(v.name).lower()
                if "amharic" in lname or "amh" in lname:
                    chosen = vid
                    break
            self.tts.say_async(s.amharic, voice_id=chosen)

    def update_progress_for_sentence(self, lesson_id, sentence_id):
        if not self.current_user:
            return
        key = f"l{lesson_id}"
        prog = self.progress.get(key, {"seen": []})
        if sentence_id not in prog["seen"]:
            prog["seen"].append(sentence_id)
        self.progress[key] = prog
        save_progress(self.current_user_id, self.progress)
        self.update_progress_ui()

    def update_progress_ui(self):
        if not self.current_user:
            self.progress_label.config(text="Progress: Not logged in")
            return
        # compute summary
        total_seen = sum(len(v.get("seen", [])) for v in self.progress.values())
        self.progress_label.config(text=f"Progress: {total_seen} items seen")

    # --- Vocabulary builder & exercises ---
    def open_vocab_builder(self):
        if not self.selected_lesson:
            messagebox.showinfo("Select lesson", "Please select a lesson first.")
            return
        d = tk.Toplevel(self.root)
        d.title("Vocabulary Builder")
        vs = self.selected_lesson.vocabulary
        tree = ttk.Treeview(d, columns=("am", "ex"), show="headings")
        tree.heading("am", text="Amharic")
        tree.heading("ex", text="Example")
        tree.pack(fill=tk.BOTH, expand=True)
        for v in vs:
            tree.insert("", tk.END, values=(f"{v['word']} — {v['translation']}", v.get("example","")))
        def play_item():
            sel = tree.selection()
            if not sel:
                return
            val = tree.item(sel[0], "values")[0]
            # extract english word before ' — '
            eng = val.split("—")[0].strip()
            # play english then amharic translation
            self.tts.say_async(eng)
            # find translation
            for v in vs:
                if v['word'] == eng:
                    self.tts.say_async(v['translation'])
                    break
        ttk.Button(d, text="Play Selected", command=play_item).pack(pady=6)

    def open_exercises(self):
        if not self.selected_lesson:
            messagebox.showinfo("Select lesson", "Please select a lesson first.")
            return
        d = tk.Toplevel(self.root)
        d.title("Exercises")
        nb = ttk.Notebook(d)
        nb.pack(fill=tk.BOTH, expand=True)

        # matching
        frame1 = ttk.Frame(nb)
        nb.add(frame1, text="Matching")
        engs, amhs = generate_matching(self.selected_lesson.vocabulary)
        ttk.Label(frame1, text="Match English (left) to Amharic (right)").pack()
        left = tk.Listbox(frame1)
        left.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=6, pady=6)
        for e in engs:
            left.insert(tk.END, e)
        right = tk.Listbox(frame1)
        right.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=6, pady=6)
        for a in amhs:
            right.insert(tk.END, a)
        def check_matching():
            sel_l = left.curselection()
            sel_r = right.curselection()
            if not sel_l or not sel_r:
                messagebox.showinfo("Select", "Select one from each list")
                return
            e = left.get(sel_l[0])
            a = right.get(sel_r[0])
            # verify
            correct = next((v for v in self.selected_lesson.vocabulary if v['word']==e), None)
            if correct and correct['translation']==a:
                messagebox.showinfo("Correct", "Good job!")
            else:
                messagebox.showinfo("Try again", "Not a match.")
        ttk.Button(frame1, text="Check Match", command=check_matching).pack(pady=6)

        # fill in the blank
        frame2 = ttk.Frame(nb)
        nb.add(frame2, text="Fill in the blank")
        # pick a random sentence and a target vocab word
        import random
        sent = random.choice(self.selected_lesson.sentences)
        if self.selected_lesson.vocabulary:
            target = random.choice(self.selected_lesson.vocabulary)['word']
        else:
            # fallback to first word
            target = sent.english.split()[0]
        blanked = generate_fill_blank(sent.english, target)
        ttk.Label(frame2, text=f"{blanked}").pack(padx=6, pady=6)
        ans_entry = ttk.Entry(frame2)
        ans_entry.pack(padx=6, pady=6)
        def check_blank():
            if ans_entry.get().strip().lower() == target.lower():
                messagebox.showinfo("Correct", "Well done!")
            else:
                messagebox.showinfo("Incorrect", f"Answer was: {target}")
        ttk.Button(frame2, text="Check", command=check_blank).pack(pady=6)

        # multiple-choice
        frame3 = ttk.Frame(nb)
        nb.add(frame3, text="Multiple Choice")
        # pick a sentence and create options from vocabulary
        if self.selected_lesson.vocabulary:
            vocab_words = [v['word'] for v in self.selected_lesson.vocabulary]
            q_word = vocab_words[0]
            # build choices
            choices = vocab_words[:]
            while len(choices) < 4:
                choices.append("placeholder")
            import random
            random.shuffle(choices)
            ttk.Label(frame3, text=f"What is the translation of '{q_word}'?").pack(pady=6)
            var = tk.StringVar()
            for c in choices[:4]:
                ttk.Radiobutton(frame3, text=c, variable=var, value=c).pack(anchor=tk.W)
            def check_mc():
                sel = var.get()
                if not sel:
                    messagebox.showinfo("Choose", "Please choose an option")
                    return
                real = next((v['translation'] for v in self.selected_lesson.vocabulary if v['word']==q_word), None)
                if sel == real:
                    messagebox.showinfo("Correct", "Nice!")
                else:
                    messagebox.showinfo("Wrong", f"Correct answer: {real}")
            ttk.Button(frame3, text="Submit", command=check_mc).pack(pady=6)
