import os
import math
import zipfile
import tempfile
import streamlit as st

try:
    from moviepy import AudioFileClip
except ImportError:
    from moviepy.editor import AudioFileClip

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Audio Splitter",
    page_icon="🎙️",
    layout="centered",
)

st.title("🎙️ Audio Splitter")
st.caption("Upload one or more audio files and download them sliced into 4-minute batches.")

# ── Sidebar settings ──────────────────────────────────────────────────────────
with st.sidebar:
    st.header("⚙️ Settings")
    chunk_minutes = st.number_input(
        "Chunk length (minutes)", min_value=1, max_value=60, value=4, step=1
    )
    output_format = st.selectbox("Output format", ["mp3", "wav", "m4a"], index=0)
    st.markdown("---")
    st.info("Supported uploads: `.m4a` `.mp3` `.wav` `.aac`")

chunk_length = chunk_minutes * 60  # seconds

# ── File uploader ─────────────────────────────────────────────────────────────
uploaded_files = st.file_uploader(
    "Upload audio file(s)",
    type=["m4a", "mp3", "wav", "aac"],
    accept_multiple_files=True,
)

if not uploaded_files:
    st.info("👆 Upload at least one audio file to get started.")
    st.stop()

# ── Process button ────────────────────────────────────────────────────────────
if st.button("✂️ Split Audio", type="primary", use_container_width=True):

    zip_buffer_path = tempfile.mktemp(suffix=".zip")

    with tempfile.TemporaryDirectory() as tmp_dir:
        all_results = []

        for uploaded_file in uploaded_files:
            st.markdown(f"---\n### 🎵 `{uploaded_file.name}`")

            # Save upload to a temp file so MoviePy can read it
            suffix = os.path.splitext(uploaded_file.name)[1]
            tmp_input = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
            tmp_input.write(uploaded_file.read())
            tmp_input.flush()
            tmp_input.close()

            try:
                audio = AudioFileClip(tmp_input.name)
                duration = audio.duration
                total_batches = math.ceil(duration / chunk_length)

                st.write(
                    f"⏱️ Duration: **{duration/60:.1f} min** → "
                    f"**{total_batches} batch{'es' if total_batches != 1 else ''}** "
                    f"of {chunk_minutes} min each"
                )

                # Output sub-folder inside tmp_dir
                base_name = os.path.splitext(uploaded_file.name)[0]
                folder_name = f"{base_name} Extraction Folder"
                output_path = os.path.join(tmp_dir, folder_name)
                os.makedirs(output_path, exist_ok=True)

                progress = st.progress(0, text="Slicing…")

                for i in range(total_batches):
                    start_t = i * chunk_length
                    end_t = min((i + 1) * chunk_length, duration)

                    chunk = audio.subclipped(start_t, end_t)
                    batch_filename = f"{base_name} Batch {i+1}.{output_format}"
                    chunk.write_audiofile(
                        os.path.join(output_path, batch_filename),
                        logger=None,
                    )

                    progress.progress(
                        (i + 1) / total_batches,
                        text=f"Batch {i+1}/{total_batches} done",
                    )

                audio.close()
                progress.empty()

                # List output files
                batch_files = sorted(os.listdir(output_path))
                st.success(f"✅ {len(batch_files)} batches created")
                with st.expander("📂 View batch files"):
                    for bf in batch_files:
                        st.write(f"• {bf}")

                all_results.extend(
                    [os.path.join(output_path, bf) for bf in batch_files]
                )

            except Exception as e:
                st.error(f"❌ Error processing `{uploaded_file.name}`: {e}")
            finally:
                os.unlink(tmp_input.name)

        # ── Pack everything into a ZIP ─────────────────────────────────────
        if all_results:
            with zipfile.ZipFile(zip_buffer_path, "w", zipfile.ZIP_DEFLATED) as zf:
                for file_path in all_results:
                    # Keep the folder structure inside the ZIP
                    arcname = os.path.relpath(file_path, tmp_dir)
                    zf.write(file_path, arcname)

    # ── Download button ────────────────────────────────────────────────────
    st.markdown("---")
    if os.path.exists(zip_buffer_path):
        with open(zip_buffer_path, "rb") as f:
            zip_bytes = f.read()
        os.unlink(zip_buffer_path)

        st.download_button(
            label="⬇️ Download All Batches (.zip)",
            data=zip_bytes,
            file_name="audio_batches.zip",
            mime="application/zip",
            use_container_width=True,
            type="primary",
        )
        st.caption("The ZIP preserves the per-file folder structure from the original script.")
