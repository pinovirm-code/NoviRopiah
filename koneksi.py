from flask import Flask, render_template, request, redirect, url_for, make_response, send_file
import mysql.connector
from fpdf import FPDF
import os
import datetime

app = Flask(__name__)

db_config = {
    'host': 'localhost',
    'user': 'root',
    'password': '',
    'database': 'db_rapor_novi'
}

def get_db_connection():
    return mysql.connector.connect(**db_config)

def generate_id_nilai():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT id_nilai
        FROM tb_nilai_novi
        WHERE id_nilai LIKE 'NLI%'
        ORDER BY CAST(SUBSTRING(id_nilai, 4) AS UNSIGNED) DESC
        LIMIT 1
    """)
    row = cursor.fetchone()

    if row:
        nomor = int(row['id_nilai'][3:]) + 1
    else:
        nomor = 1

    cursor.close()
    conn.close()

    return f"NLI{nomor:03d}"

class PDF(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 14)
        self.ln(5)

@app.route('/')
def index():
    return redirect(url_for('daftar_nilai'))

@app.route('/nilai')
def daftar_nilai():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # Ambil parameter filter dari URL
    kelas = request.args.get('kelas', '')
    semester = request.args.get('semester', '')
    tahun_ajaran = request.args.get('tahun_ajaran', '')

    # Query dasar
    query = """
        SELECT
            n.id_nilai,
            s.nis,
            s.nama_siswa,
            k.nama_kelas,
            m.nama_mapel,
            n.nilai_tugas,
            n.nilai_uts,
            n.nilai_uas,
            n.deskripsi,
            ROUND((n.nilai_tugas + n.nilai_uts + n.nilai_uas) / 3, 2) AS nilai_akhir,
            n.semester,
            n.tahun_ajaran
        FROM tb_nilai_novi n
        JOIN tb_siswa_novi s ON n.nis = s.nis
        JOIN tb_kelas_novi k ON s.id_kelas = k.id_kelas
        JOIN tb_mapel_novi m ON n.id_mapel = m.id_mapel
        WHERE 1=1
    """
    
    params = []
    
    # Tambahkan filter berdasarkan parameter
    if kelas:
        query += " AND k.nama_kelas = %s"
        params.append(kelas)
    
    if semester:
        query += " AND n.semester = %s"
        params.append(semester)
    
    if tahun_ajaran:
        query += " AND n.tahun_ajaran = %s"
        params.append(tahun_ajaran)
    
    query += " ORDER BY s.nama_siswa, m.nama_mapel"

    cursor.execute(query, params)
    data = cursor.fetchall()

    # Ambil daftar kelas untuk dropdown filter
    cursor.execute("SELECT DISTINCT nama_kelas FROM tb_kelas_novi ORDER BY nama_kelas")
    kelas_list = cursor.fetchall()

    # Ambil daftar semester unik untuk dropdown
    cursor.execute("SELECT DISTINCT semester FROM tb_nilai_novi ORDER BY semester")
    semester_list = cursor.fetchall()

    # Ambil daftar tahun ajaran unik untuk dropdown
    cursor.execute("SELECT DISTINCT tahun_ajaran FROM tb_nilai_novi ORDER BY tahun_ajaran DESC")
    tahun_ajaran_list = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template('hasil_koneksi.html', 
                         siswa=data, 
                         kelas_list=kelas_list,
                         semester_list=semester_list,
                         tahun_ajaran_list=tahun_ajaran_list,
                         filter_kelas=kelas,
                         filter_semester=semester,
                         filter_tahun_ajaran=tahun_ajaran)

@app.route('/edit_nilai/<id_nilai>', methods=['GET', 'POST'])
def edit_nilai(id_nilai):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    if request.method == 'POST':
        id_mapel = request.form['id_mapel']
        nilai_tugas = request.form['nilai_tugas']
        nilai_uts = request.form['nilai_uts']
        nilai_uas = request.form['nilai_uas']
        semester = request.form['semester']
        tahun_ajaran = request.form['tahun_ajaran']
        deskripsi = request.form['deskripsi']

        query = """
        UPDATE tb_nilai_novi SET
            id_mapel=%s,
            nilai_tugas=%s,
            nilai_uts=%s,
            nilai_uas=%s,
            semester=%s,
            tahun_ajaran=%s,
            deskripsi=%s
        WHERE id_nilai=%s
        """

        cursor.execute(query, (
            id_mapel,
            nilai_tugas,
            nilai_uts,
            nilai_uas,
            semester,
            tahun_ajaran,
            deskripsi,
            id_nilai
        ))

        conn.commit()
        cursor.close()
        conn.close()
        return redirect(url_for('daftar_nilai'))

    cursor.execute("""
        SELECT n.*, m.nama_mapel
        FROM tb_nilai_novi n
        JOIN tb_mapel_novi m ON n.id_mapel = m.id_mapel
        WHERE n.id_nilai=%s
    """, (id_nilai,))
    nilai = cursor.fetchone()

    cursor.execute("SELECT id_mapel, nama_mapel FROM tb_mapel_novi")
    mapel = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template('edit_nilai.html', nilai=nilai, mapel=mapel)

@app.route('/delete_nilai/<id_nilai>')
def delete_nilai(id_nilai):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("DELETE FROM tb_nilai_novi WHERE id_nilai=%s", (id_nilai,))
    conn.commit()

    cursor.close()
    conn.close()

    return redirect(url_for('daftar_nilai'))

@app.route('/tambah_nilai', methods=['GET', 'POST'])
def tambah_nilai():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    if request.method == 'POST':
        id_nilai = generate_id_nilai()
        nis = request.form['nis']
        id_mapel = request.form['id_mapel']
        nilai_tugas = request.form['nilai_tugas']
        nilai_uts = request.form['nilai_uts']
        nilai_uas = request.form['nilai_uas']
        semester = request.form['semester']
        tahun_ajaran = request.form['tahun_ajaran']
        deskripsi = request.form['deskripsi']

        query = """
            INSERT INTO tb_nilai_novi
            (id_nilai, nis, id_mapel, nilai_tugas, nilai_uts, nilai_uas,
             semester, tahun_ajaran, deskripsi)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """
        cursor.execute(query, (
            id_nilai, nis, id_mapel,
            nilai_tugas, nilai_uts, nilai_uas,
            semester, tahun_ajaran, deskripsi
        ))
        conn.commit()

        cursor.close()
        conn.close()
        return redirect(url_for('daftar_nilai'))

    cursor.execute("SELECT nis, nama_siswa FROM tb_siswa_novi")
    siswa = cursor.fetchall()

    cursor.execute("SELECT id_mapel, nama_mapel FROM tb_mapel_novi")
    mapel = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template('tambah_nilai.html', siswa=siswa, mapel=mapel)

# ======================= CETAK HTML =======================
@app.route('/cetak/<nis>')
def cetak_rapor(nis):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT s.nis, s.nama_siswa, k.nama_kelas
        FROM tb_siswa_novi s
        JOIN tb_kelas_novi k ON s.id_kelas = k.id_kelas
        WHERE s.nis = %s
    """, (nis,))
    siswa = cursor.fetchone()

    cursor.execute("""
        SELECT m.nama_mapel,
               n.nilai_tugas,
               n.nilai_uts,
               n.nilai_uas,
               ROUND((n.nilai_tugas + n.nilai_uts + n.nilai_uas)/3, 2) AS nilai_akhir,
               n.deskripsi,
               n.semester,
               n.tahun_ajaran,
               COALESCE(n.sakit, 0) as sakit,
               COALESCE(n.catatan_wali_kelas, 'Ananda menunjukkan perkembangan belajar yang baik selama semester ini.') as catatan_wali_kelas
        FROM tb_nilai_novi n
        JOIN tb_mapel_novi m ON n.id_mapel = m.id_mapel
        WHERE n.nis = %s
        ORDER BY m.nama_mapel
    """, (nis,))
    nilai = cursor.fetchall()

    cursor.close()
    conn.close()

    # Hitung total sakit dan ambil catatan wali kelas
    sakit_hari = 0
    catatan_wali = "Ananda menunjukkan perkembangan belajar yang baik selama semester ini."
    
    if nilai:
        sakit_hari = nilai[0]['sakit']
        if nilai[0]['catatan_wali_kelas']:
            catatan_wali = nilai[0]['catatan_wali_kelas']

    return render_template('cetak_rapor.html', 
                         siswa=siswa, 
                         nilai=nilai,
                         sakit_hari=sakit_hari,
                         catatan_wali=catatan_wali)

# ======================= CETAK PDF SISWA INDIVIDU =======================
# ======================= CETAK PDF SISWA INDIVIDU =======================
@app.route('/cetak_pdf/<nis>')
def cetak_pdf_siswa(nis):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        # Ambil data siswa
        cursor.execute("""
            SELECT s.nis, s.nama_siswa, k.nama_kelas
            FROM tb_siswa_novi s
            JOIN tb_kelas_novi k ON s.id_kelas = k.id_kelas
            WHERE s.nis = %s
        """, (nis,))
        siswa = cursor.fetchone()

        if not siswa:
            cursor.close()
            conn.close()
            return "Data siswa tidak ditemukan"

        # Ambil data nilai dengan sakit, izin, dan tanpa keterangan
        cursor.execute("""
            SELECT m.nama_mapel,
                   n.nilai_tugas,
                   n.nilai_uts,
                   n.nilai_uas,
                   ROUND((n.nilai_tugas + n.nilai_uts + n.nilai_uas)/3, 2) AS nilai_akhir,
                   n.deskripsi,
                   n.semester,
                   n.tahun_ajaran,
                   COALESCE(n.sakit, 0) as sakit,
                   COALESCE(n.izin, 0) as izin,
                   COALESCE(n.tanpa_keterangan, 0) as tanpa_keterangan,
                   COALESCE(n.catatan_wali_kelas, 'Ananda menunjukkan perkembangan belajar yang baik selama semester ini.') as catatan_wali_kelas
            FROM tb_nilai_novi n
            JOIN tb_mapel_novi m ON n.id_mapel = m.id_mapel
            WHERE n.nis = %s
            ORDER BY m.nama_mapel
        """, (nis,))
        nilai = cursor.fetchall()

        cursor.close()
        conn.close()


        sakit_hari = 0
        izin_hari = 0
        tanpa_keterangan_hari = 0
        catatan_wali = "Ananda menunjukkan perkembangan belajar yang baik selama semester ini."
        
        if nilai and len(nilai) > 0:
            sakit_hari = nilai[0]['sakit'] if nilai[0]['sakit'] is not None else 0
            izin_hari = nilai[0]['izin'] if nilai[0]['izin'] is not None else 0
            tanpa_keterangan_hari = nilai[0]['tanpa_keterangan'] if nilai[0]['tanpa_keterangan'] is not None else 0
            if nilai[0]['catatan_wali_kelas']:
                catatan_wali = str(nilai[0]['catatan_wali_kelas'])

        # Buat PDF dengan format A4
        pdf = FPDF('P', 'mm', 'A4')
        pdf.add_page()
        
        # ========== KOP SURAT / HEADER SEKOLAH ==========
        # Logo atau nama sekolah di tengah
        pdf.set_font('Arial', 'B', 16)
        pdf.cell(0, 10, 'SEKOLAH MENENGAH KEJURUAN', 0, 1, 'C')
        pdf.set_font('Arial', 'B', 18)
        pdf.cell(0, 10, 'SMK NEGERI 2 CIMAHI', 0, 1, 'C')
        pdf.set_font('Arial', '', 10)
        pdf.cell(0, 6, 'Jl.  Jl. Kamarung KM. 1,5 No. 69, Kelurahan Citeureup, Kecamatan Cimahi Utara, Kota Cimahi.', 0, 1, 'C')
        pdf.cell(0, 6, 'Telp: (0341) 123456 | Email: smkn2cimahi@sch.id', 0, 1, 'C')
        
        # Garis pembatas
        pdf.set_line_width(1)
        pdf.line(10, pdf.get_y(), 200, pdf.get_y())
        pdf.ln(10)

        # Tabel identitas
        pdf.set_font('Arial', '', 11)
        
        # Baris 1
        pdf.cell(40, 8, 'NIS', 0, 0)
        pdf.cell(5, 8, ':', 0, 0)
        pdf.cell(60, 8, str(siswa['nis']), 0, 0)
        
        pdf.cell(30, 8, 'Kelas', 0, 0)
        pdf.cell(5, 8, ':', 0, 0)
        pdf.cell(0, 8, str(siswa['nama_kelas']), 0, 1)
        
        # Baris 2
        pdf.cell(40, 8, 'Nama Siswa', 0, 0)
        pdf.cell(5, 8, ':', 0, 0)
        pdf.cell(60, 8, str(siswa['nama_siswa']), 0, 0)
        
        pdf.cell(30, 8, 'Semester', 0, 0)
        pdf.cell(5, 8, ':', 0, 0)
        semester_val = str(nilai[0]['semester']).upper() if nilai and len(nilai) > 0 else ''
        pdf.cell(0, 8, semester_val, 0, 1)
        
        # Baris 3
        pdf.cell(40, 8, 'Tahun Ajaran', 0, 0)
        pdf.cell(5, 8, ':', 0, 0)
        tahun_val = str(nilai[0]['tahun_ajaran']) if nilai and len(nilai) > 0 else ''
        pdf.cell(60, 8, tahun_val, 0, 0)
        
        pdf.cell(30, 8, 'Tingkat', 0, 0)
        pdf.cell(5, 8, ':', 0, 0)
        # Ambil tingkat dari nama kelas (misal: XI ANIMASI A -> XI)
        kelas_parts = str(siswa['nama_kelas']).split()
        tingkat = kelas_parts[0] if len(kelas_parts) > 0 else ''
        pdf.cell(0, 8, tingkat, 0, 1)
        
        pdf.ln(10)
        
        # ========== DATA KEHADIRAN ==========
        pdf.set_font('Arial', 'B', 12)
        pdf.cell(0, 10, 'DATA KEHADIRAN', 0, 1)
        pdf.set_line_width(0.3)
        pdf.line(10, pdf.get_y(), 200, pdf.get_y())
        pdf.ln(5)
        
        pdf.set_font('Arial', '', 11)
        # Tabel kehadiran
        col_width = 60
        pdf.cell(col_width, 8, 'Jenis Ketidakhadiran', 1, 0, 'C')
        pdf.cell(col_width, 8, 'Jumlah Hari', 1, 0, 'C')
        pdf.cell(col_width, 8, 'Keterangan', 1, 1, 'C')
        
        pdf.cell(col_width, 8, 'Sakit', 1, 0)
        pdf.cell(col_width, 8, str(sakit_hari) + ' hari', 1, 0, 'C')
        pdf.cell(col_width, 8, 'Dengan surat dokter', 1, 1)
        
        pdf.cell(col_width, 8, 'Izin', 1, 0)
        pdf.cell(col_width, 8, str(izin_hari) + ' hari', 1, 0, 'C')
        pdf.cell(col_width, 8, 'Dengan surat izin', 1, 1)
        
        pdf.cell(col_width, 8, 'Tanpa Keterangan', 1, 0)
        pdf.cell(col_width, 8, str(tanpa_keterangan_hari) + ' hari', 1, 0, 'C')
        pdf.cell(col_width, 8, 'Alpa', 1, 1)
        
        pdf.ln(10)
        
        # ========== NILAI AKADEMIK ==========
        pdf.set_font('Arial', 'B', 12)
        pdf.cell(0, 10, 'NILAI AKADEMIK', 0, 1)
        pdf.set_line_width(0.3)
        pdf.line(10, pdf.get_y(), 200, pdf.get_y())
        pdf.ln(5)
        
        # Header tabel nilai
        pdf.set_font('Arial', 'B', 10)
        col_widths = [60, 20, 20, 20, 25, 45]  # Total: 190mm
        
        headers = ['Mata Pelajaran', 'Tugas', 'UTS', 'UAS', 'Nilai Akhir', 'Deskripsi']
        
        for i, header in enumerate(headers):
            pdf.cell(col_widths[i], 10, header, 1, 0, 'C')
        pdf.ln()
        
        # Isi tabel nilai
        pdf.set_font('Arial', '', 10)
        for d in nilai:
            # Mata Pelajaran
            nama_mapel = str(d['nama_mapel']) if d['nama_mapel'] else ""
            pdf.cell(col_widths[0], 8, nama_mapel, 1)
            
            # Nilai
            nilai_tugas = str(d['nilai_tugas']) if d['nilai_tugas'] is not None else "0"
            nilai_uts = str(d['nilai_uts']) if d['nilai_uts'] is not None else "0"
            nilai_uas = str(d['nilai_uas']) if d['nilai_uas'] is not None else "0"
            nilai_akhir = str(d['nilai_akhir']) if d['nilai_akhir'] is not None else "0"
            
            pdf.cell(col_widths[1], 8, nilai_tugas, 1, 0, 'C')
            pdf.cell(col_widths[2], 8, nilai_uts, 1, 0, 'C')
            pdf.cell(col_widths[3], 8, nilai_uas, 1, 0, 'C')
            pdf.cell(col_widths[4], 8, nilai_akhir, 1, 0, 'C')
            
            # Deskripsi
            deskripsi = str(d['deskripsi']) if d['deskripsi'] else ""
            pdf.cell(col_widths[5], 8, deskripsi, 1, 1)
        
        pdf.ln(10)
        
        # ========== CATATAN WALI KELAS ==========
        pdf.set_font('Arial', 'B', 12)
        pdf.cell(0, 10, 'CATATAN WALI KELAS', 0, 1)
        pdf.set_line_width(0.3)
        pdf.line(10, pdf.get_y(), 200, pdf.get_y())
        pdf.ln(9)
        
        pdf.set_font('Arial', '', 11)
        # Buat border untuk catatan wali kelas - PERBAIKAN DI SINI
        pdf.set_fill_color(240, 240, 240)
        
        # Method multi_cell yang benar:
        # multi_cell(w, h, txt, border=0, align='J', fill=False, ln=1, max_line_height=None, ...)
        # Kita ingin: border=1, align='L', fill=True, ln=1
        pdf.multi_cell(0, 8, str(catatan_wali), border=1, align='L', fill=True)
        
        pdf.ln(15)
        
        # ========== TANDA TANGAN ==========
        # Kolom kiri - Orang Tua/Wali
        pdf.set_font('Arial', '', 11)
        pdf.cell(80, 8, 'Mengetahui,', 0, 0, 'C')
        pdf.cell(40, 8, '', 0, 0)  # Spacer
        pdf.cell(80, 8, 'Cimahi, ' + datetime.datetime.now().strftime('%d %B %Y'), 0, 1, 'C')
        
        pdf.ln(15)
        
        # Tanda tangan Orang Tua/Wali
        pdf.cell(80, 8, 'Orang Tua/Wali Siswa', 0, 0, 'C')
        pdf.cell(40, 8, '', 0, 0)  # Spacer
        pdf.cell(80, 8, 'Wali Kelas', 0, 1, 'C')
        
        pdf.ln(20)
        
        # Garis tanda tangan
        pdf.cell(80, 1, '', 0, 0, 'C')
        pdf.cell(40, 1, '', 0, 0)
        pdf.cell(80, 1, '', 0, 1, 'C')
        
        pdf.set_font('Arial', 'U', 11)
        pdf.cell(80, 8, '____________________', 0, 0, 'C')
        pdf.cell(40, 8, '', 0, 0)
        pdf.cell(80, 8, '____________________', 0, 1, 'C')
        
        pdf.set_font('Arial', '', 9)
        pdf.cell(80, 5, 'Nama & Tanda Tangan', 0, 0, 'C')
        pdf.cell(40, 5, '', 0, 0)
        pdf.cell(80, 5, 'NIP. __________________', 0, 1, 'C')
        
        pdf.ln(10)
        

        file_name = f"Rapor_{str(siswa['nis'])}_{str(siswa['nama_siswa']).replace(' ', '_')}.pdf"
        file_path = f"temp_{file_name}"
        
        pdf.output(file_path)
        
        response = send_file(
            file_path,
            as_attachment=True,
            download_name=file_name,
            mimetype='application/pdf'
        )
        
        @response.call_on_close
        def cleanup():
            try:
                os.remove(file_path)
            except:
                pass
        
        return response
        
    except Exception as e:
        print(f"Error generating PDF: {str(e)}")
        import traceback
        traceback.print_exc()
        
        if cursor:
            cursor.close()
        if conn:
            conn.close()
            
        return f"Terjadi error saat membuat PDF: {str(e)}", 500

# ======================= CETAK PDF DAFTAR NILAI (SEMUA DATA) =======================
@app.route('/cetak_pdf_daftar_nilai')
def cetak_pdf_daftar_nilai():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        # Ambil parameter filter dari URL
        kelas = request.args.get('kelas', '')
        semester = request.args.get('semester', '')
        tahun_ajaran = request.args.get('tahun_ajaran', '')

        # Query dasar
        query = """
            SELECT
                n.id_nilai,
                s.nis,
                s.nama_siswa,
                k.nama_kelas,
                m.nama_mapel,
                n.nilai_tugas,
                n.nilai_uts,
                n.nilai_uas,
                n.deskripsi,
                ROUND((n.nilai_tugas + n.nilai_uts + n.nilai_uas) / 3, 2) AS nilai_akhir,
                n.semester,
                n.tahun_ajaran
            FROM tb_nilai_novi n
            JOIN tb_siswa_novi s ON n.nis = s.nis
            JOIN tb_kelas_novi k ON s.id_kelas = k.id_kelas
            JOIN tb_mapel_novi m ON n.id_mapel = m.id_mapel
            WHERE 1=1
        """
        
        params = []
        
        # Tambahkan filter berdasarkan parameter
        if kelas:
            query += " AND k.nama_kelas = %s"
            params.append(kelas)
        
        if semester:
            query += " AND n.semester = %s"
            params.append(semester)
        
        if tahun_ajaran:
            query += " AND n.tahun_ajaran = %s"
            params.append(tahun_ajaran)
        
        query += " ORDER BY s.nama_siswa, m.nama_mapel"

        cursor.execute(query, params)
        data = cursor.fetchall()

        cursor.close()
        conn.close()

        # Buat PDF dengan orientasi landscape
        pdf = FPDF(orientation='L')
        pdf.add_page()
        
        # Header
        pdf.set_font('Arial', 'B', 16)
        pdf.cell(0, 10, 'DAFTAR NILAI SISWA', 0, 1, 'C')
        pdf.ln(5)
        
        # Info Filter
        pdf.set_font('Arial', '', 10)
        filter_info = "Filter: "
        if kelas:
            filter_info += f"Kelas: {kelas} "
        if semester:
            filter_info += f"Semester: {semester} "
        if tahun_ajaran:
            filter_info += f"Tahun Ajaran: {tahun_ajaran}"
        if not kelas and not semester and not tahun_ajaran:
            filter_info += "Semua Data"
        
        pdf.cell(0, 8, str(filter_info), 0, 1)
        pdf.cell(0, 8, f"Total Data: {len(data)} nilai", 0, 1)
        pdf.ln(5)
        
        # Tabel
        pdf.set_font('Arial', 'B', 8)
        
        # Lebar kolom untuk landscape
        col_widths = [10, 15, 15, 35, 20, 35, 12, 12, 12, 18, 15, 25, 40]
        
        # Header tabel
        headers = ['No', 'ID', 'NIS', 'Nama Siswa', 'Kelas', 'Mata Pelajaran', 
                   'Tugas', 'UTS', 'UAS', 'Nilai Akhir', 'Semester', 'Tahun Ajaran', 'Deskripsi']
        
        for i, header in enumerate(headers):
            pdf.cell(col_widths[i], 8, header, 1, 0, 'C')
        pdf.ln()
        
        # Isi tabel
        pdf.set_font('Arial', '', 7)
        for idx, row in enumerate(data, 1):
            # No
            pdf.cell(col_widths[0], 8, str(idx), 1, 0, 'C')
            
            # ID Nilai
            id_nilai = str(row['id_nilai'])
            if len(id_nilai) > 10:
                id_nilai = id_nilai[:8] + "..."
            pdf.cell(col_widths[1], 8, id_nilai, 1)
            
            # NIS
            pdf.cell(col_widths[2], 8, str(row['nis']), 1)
            
            # Nama Siswa
            nama = str(row['nama_siswa'])
            if len(nama) > 20:
                nama = nama[:18] + "..."
            pdf.cell(col_widths[3], 8, nama, 1)
            
            # Kelas
            kelas_nama = str(row['nama_kelas'])
            pdf.cell(col_widths[4], 8, kelas_nama, 1)
            
            # Mata Pelajaran
            mapel = str(row['nama_mapel'])
            if len(mapel) > 20:
                mapel = mapel[:18] + "..."
            pdf.cell(col_widths[5], 8, mapel, 1)
            
            # Tugas
            tugas = str(row['nilai_tugas'])
            pdf.cell(col_widths[6], 8, tugas, 1, 0, 'C')
            
            # UTS
            uts = str(row['nilai_uts'])
            pdf.cell(col_widths[7], 8, uts, 1, 0, 'C')
            
            # UAS
            uas = str(row['nilai_uas'])
            pdf.cell(col_widths[8], 8, uas, 1, 0, 'C')
            
            # Nilai Akhir
            nilai_akhir = str(row['nilai_akhir'])
            pdf.cell(col_widths[9], 8, nilai_akhir, 1, 0, 'C')
            
            # Semester
            semester_val = str(row['semester'])
            pdf.cell(col_widths[10], 8, semester_val, 1, 0, 'C')
            
            # Tahun Ajaran
            tahun = str(row['tahun_ajaran'])
            pdf.cell(col_widths[11], 8, tahun, 1, 0, 'C')
            
            # Deskripsi
            deskripsi = str(row['deskripsi'])
            if len(deskripsi) > 30:
                deskripsi = deskripsi[:28] + "..."
            pdf.cell(col_widths[12], 8, deskripsi, 1, 1)
        
        # Footer
        pdf.ln(10)
        pdf.set_font('Arial', 'I', 8)
        pdf.cell(0, 8, f"Dicetak pada: {datetime.datetime.now().strftime('%d/%m/%Y %H:%M:%S')}", 0, 1)
        pdf.cell(0, 8, "Sistem Informasi Sekolah", 0, 1, 'C')

        file_name = f"Daftar_Nilai_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        file_path = f"temp_{file_name}"
        
        pdf.output(file_path)
        
        response = send_file(
            file_path,
            as_attachment=True,
            download_name=file_name,
            mimetype='application/pdf'
        )
        
        @response.call_on_close
        def cleanup():
            try:
                os.remove(file_path)
            except:
                pass
        
        return response
        
    except Exception as e:
        print(f"Error generating PDF: {str(e)}")
        import traceback
        traceback.print_exc()
        
        if cursor:
            cursor.close()
        if conn:
            conn.close()
            
        return f"Terjadi error saat membuat PDF: {str(e)}", 500

if __name__ == '__main__':
    app.run(debug=True)