<?php

namespace Database\Seeders;

use App\Models\Pegawai;
use Illuminate\Database\Console\Seeds\WithoutModelEvents;
use Illuminate\Database\Seeder;

class PegawaiSeeder extends Seeder {
    /**
     * Run the database seeds.
     */
    public function run(): void {
        Pegawai::create([
            "nama" => "Munawir, SE.,MM",
            "nip" => "196908031992111001",
            "nip9" => "340013391",
            "pangkat" => "IV",
            "golongan" => "b",
            "jabatan" => "Kepala BPS Kabupaten Mempawah",
            "email" => "munawir@bps.go.id",
            "atasan_langsung_id" => "196908031992111001",
            "unit_kerja" => "BPS Kabupaten Mempawah",
            "nomor_wa" => "6281258306655",
            "panggilan" => "Pak Munawir"
        ]);
        Pegawai::create([
            "nama" => "Muhammad Adwin, S.Mn.",
            "nip" => "198008112005021004",
            "nip9" => "340017573",
            "pangkat" => "III",
            "golongan" => "b",
            "jabatan" => "Kepala Sub Bagian Umum",
            "email" => "muh.adwin@bps.go.id",
            "atasan_langsung_id" => "196908031992111001",
            "nomor_wa" => "6285346332883",
            "unit_kerja" => "BPS Kabupaten Mempawah",
            "panggilan" => "Bg Adwin"
        ]);
        Pegawai::create([
            "nama" => "Rifky Mullah Syadriawan A.Md.Stat.",
            "nip" => "200110202023021003",
            "nip9" => "340062230",
            "pangkat" => "II",
            "golongan" => "c",
            "jabatan" => "Pengatur",
            "email" => "mullahrifky@bps.go.id",
            "nomor_wa" => "62895704961475",
            "atasan_langsung_id" => "196908031992111001",
            "panggilan" => "Bg Rifky",
            "unit_kerja" => "BPS Kabupaten Mempawah",
        ]);
        Pegawai::create([
            "nama" => "Ihza Fikri Zaki Karunia, S.Tr.Stat.",
            "nip" => "199910282023021005",
            "nip9" => "340061823",
            "pangkat" => "III",
            "golongan" => "a",
            "jabatan" => "Pranata Komputer Ahli Pertama",
            "email" => "ihzakarunia@bps.go.id",
            "panggilan" => "Bg Ihza",
            "nomor_wa" => "6289625345646",
            "atasan_langsung_id" => "196908031992111001",
            "unit_kerja" => "BPS Kabupaten Mempawah"
        ]);
        Pegawai::create([
            "nama" => "Abdul Karim",
            "nip" => "196901192007011004",
            "nip9" => "340019770",
            "pangkat" => "II",
            "golongan" => "c",
            "panggilan" => "Pak Karim",
            "jabatan" => "Pengolah Data",
            "email" => "abdul.karim@bps.go.id",
            "nomor_wa" => "62895329522455",
            "atasan_langsung_id" => "196908031992111001",
            "unit_kerja" => "BPS Kabupaten Mempawah"
        ]);
        Pegawai::create([
            "nama" => "Budiman Aller Silaban S.Tr.Stat.",
            "nip" => "200001062023021001",
            "nip9" => "340061717",
            "panggilan" => "Bg Aller",
            "pangkat" => "III",
            "golongan" => "a",
            "jabatan" => "Statistisi Ahli Pertama",
            "email" => "allersilaban@bps.go.id",
            "nomor_wa" => "6282387765753",
            "atasan_langsung_id" => "196908031992111001",
            "unit_kerja" => "BPS Kabupaten Mempawah"
        ]);
        Pegawai::create([
            "nama" => "Arief Yuandi SST",
            "nip" => "199306062016021001",
            "panggilan" => "Bg Arief",
            "nip9" => "340057298",
            "pangkat" => "III",
            "golongan" => "d",
            "jabatan" => "Pranata Komputer Ahli Muda",
            "email" => "arief.yuandi@bps.go.id",
            "nomor_wa" => "6285787387758",
            "atasan_langsung_id" => "196908031992111001",
            "unit_kerja" => "BPS Kabupaten Mempawah"
        ]);
        Pegawai::create([
            "nama" => "Arini Faurizah S.Tr.Stat",
            "panggilan" => "Kak Arin",
            "nip" => "199605222019012001",
            "nip9" => "340058620",
            "pangkat" => "III",
            "golongan" => "b",
            "jabatan" => "Statistisi Ahli Pertama",
            "nomor_wa" => "6281281701197",
            "email" => "arinif@bps.go.id",
            "atasan_langsung_id" => "196908031992111001",
            "unit_kerja" => "BPS Kabupaten Mempawah"
        ]);
        Pegawai::create([
            "nama" => "Arsita Indah Wahyuni A.Md.Stat.",
            "panggilan" => "Kak Sita",
            "nip" => "199905272023022001",
            "nip9" => "340062135",
            "pangkat" => "II",
            "golongan" => "c",
            "jabatan" => "Pengatur",
            "nomor_wa" => "6281313526688",
            "email" => "arsita.indah@bps.go.id",
            "atasan_langsung_id" => "196908031992111001",
            "unit_kerja" => "BPS Kabupaten Mempawah"
        ]);
        Pegawai::create([
            "nama" => "Firmansyah S.E.",
            "panggilan" => "Bg Firman",
            "nip" => "198103182011011003",
            "nip9" => "340055280",
            "pangkat" => "III",
            "golongan" => "d",
            "jabatan" => "Statistisi Ahli Pertama",
            "nomor_wa" => "628982626008",
            "email" => "firmansyah2@bps.go.id",
            "atasan_langsung_id" => "196908031992111001",
            "unit_kerja" => "BPS Kabupaten Mempawah"
        ]);
        Pegawai::create([
            "nama" => "Listio Jati Nandhiko S.Tr.Stat.",
            "panggilan" => "Bg Tio",
            "nip" => "199612302019011001",
            "nip9" => "340058814",
            "pangkat" => "III",
            "golongan" => "b",
            "jabatan" => "Statistisi Ahli Pertama",
            "email" => "listiojati@bps.go.id",
            "nomor_wa" => "6285601059595",
            "atasan_langsung_id" => "196908031992111001",
            "unit_kerja" => "BPS Kabupaten Mempawah"
        ]);
        Pegawai::create([
            "nama" => "Maria Sintauli Hutauruk S.Tr.Stat.",
            "panggilan" => "Kak Maria",
            "nip" => "199608042019012001",
            "nip9" => "340058823",
            "pangkat" => "III",
            "golongan" => "b",
            "jabatan" => "Statistisi Ahli Pertama",
            "email" => "mariash@bps.go.id",
            "atasan_langsung_id" => "196908031992111001",
            "unit_kerja" => "BPS Kabupaten Toba Samosir"
        ]);
        Pegawai::create([
            "nama" => "Najia Helmiah S.Tr.Stat.",
            "nip" => "200002042022012003",
            "panggilan" => "Kak Najia",
            "nip9" => "340060805",
            "pangkat" => "III",
            "golongan" => "a",
            "jabatan" => "Statistisi Ahli Pertama",
            "nomor_wa" => "6281649436324",
            "email" => "najia.helmiah@bps.go.id",
            "atasan_langsung_id" => "196908031992111001",
            "unit_kerja" => "BPS Kabupaten Mempawah"
        ]);
        Pegawai::create([
            "nama" => "Safira Nurrosyid S.Tr.Stat.",
            "panggilan" => "Kak Safira",
            "nip" => "199606062019122001",
            "nip9" => "340059760 ",
            "pangkat" => "III",
            "golongan" => "a",
            "jabatan" => "Statistisi Ahli Pertama",
            "nomor_wa" => "6289605412110",
            "email" => "safira.nurrosyid@bps.go.id",
            "atasan_langsung_id" => "196908031992111001",
            "unit_kerja" => "BPS Kabupaten Mempawah"
        ]);
        Pegawai::create([
            "nama" => "Sarah Pratiwi S.Tr.Stat.",
            "panggilan" => "Kak Sarah",
            "nip" => "199605162019012001",
            "nip9" => "340058975",
            "pangkat" => "III",
            "golongan" => "b",
            "jabatan" => "Statistisi Ahli Pertama",
            "email" => "sarah.pratiwi@bps.go.id",
            "nomor_wa" => "6285641219375",
            "atasan_langsung_id" => "196908031992111001",
            "unit_kerja" => "BPS Kabupaten Mempawah"
        ]);
        Pegawai::create([
            "nama" => "Syarifah Apriani ST",
            "panggilan" => "Kak Ani",
            "nip" => "198204042005022005",
            "nip9" => "340017570",
            "pangkat" => "III",
            "golongan" => "d",
            "jabatan" => "Statistisi Ahli Muda",
            "email" => "sy.apriani@bps.go.id",
            "nomor_wa" => "6285750055399",
            "atasan_langsung_id" => "196908031992111001",
            "unit_kerja" => "BPS Kabupaten Mempawah"
        ]);
        Pegawai::create([
            "nama" => "Wantri Mukti Lestari S.Si.",
            "panggilan" => "Kak Tari",
            "nip" => "199101072019032001",
            "nip9" => "340059242",
            "pangkat" => "III",
            "golongan" => "b",
            "jabatan" => "Bendahara Pengeluaran",
            "nomor_wa" => "6285729270939",
            "email" => "wantri.mukti@bps.go.id",
            "atasan_langsung_id" => "196908031992111001",
            "unit_kerja" => "BPS Kabupaten Mempawah"
        ]);
        Pegawai::create([
            "nama" => "Yulfi Ramanda SE.",
            "panggilan" => "Bg Yulfi",
            "nip" => "198007142011011003",
            "nip9" => "340055305",
            "pangkat" => "III",
            "golongan" => "b",
            "jabatan" => "Statistisi Ahli Pertama",
            "email" => "yulfi.ramanda@bps.go.id",
            "nomor_wa" => "6289677526510",
            "atasan_langsung_id" => "196908031992111001",
            "unit_kerja" => "BPS Kabupaten Mempawah"
        ]);
        Pegawai::create([
            "nama" => "Ahmad Aulia Rahman, S.Tr.Stat.",
            "panggilan" => "Mas Aul",
            "nip" => "200109122024121001",
            "nip9" => "340062981",
            "pangkat" => "III",
            "golongan" => "a",
            "jabatan" => "Statistisi Ahli Pertama",
            "email" => "ahmad.aulia@bps.go.id",
            "nomor_wa" => "6285183057109",
            "atasan_langsung_id" => "196908031992111001",
            "unit_kerja" => "BPS Kabupaten Mempawah"
        ]);
        Pegawai::create([
            "nama" => "Vaniya Dewi Wulandari, A.Md.Stat.",
            "panggilan" => "Kak Vaniya",
            "nip" => "200306242024122001",
            "nip9" => "340063573",
            "pangkat" => "II",
            "golongan" => "c",
            "jabatan" => "Statistisi Terampil",
            "nomor_wa" => "6289612264631",
            "email" => "vaniya.dewi@bps.go.id",
            "atasan_langsung_id" => "196908031992111001",
            "unit_kerja" => "BPS Kabupaten Mempawah"
        ]);
        Pegawai::create([
            "nama" => "Sukma Andini, S.Tr.Stat",
            "panggilan" => "Kak Sukma",
            "nip" => "200202152024122003",
            "nip9" => "340063547",
            "pangkat" => "III",
            "golongan" => "a",
            "jabatan" => "Pranata Komputer Ahli Pertama",
            "nomor_wa" => "6282234120921",
            "email" => "sukma.andini@bps.go.id",
            "atasan_langsung_id" => "196908031992111001",
            "unit_kerja" => "BPS Kabupaten Mempawah"
        ]);
        Pegawai::create([
            "nama" => "Muhammad Syihabuddin Alhaq S.E.",
            "panggilan" => "Bg Syihab",
            "nip" => "198407112011011007",
            "nip9" => "340055291",
            "pangkat" => "III",
            "golongan" => "d",
            "jabatan" => "Statistisi Ahli Pertama",
            "nomor_wa" => "6281254454747",
            "email" => "alhaq@bps.go.id",
            "atasan_langsung_id" => "196908031992111001",
            "unit_kerja" => "BPS Kabupaten Mempawah"
        ]);
        Pegawai::create([
            "nama" => "Supandi S.Si, M.Ec.Dev",
            "panggilan" => "Mas Pandi",
            "nip" => "198603272009021005",
            "nip9" => "340051340 ",
            "pangkat" => "IV",
            "nomor_wa" => "6282353026570",
            "golongan" => "a",
            "jabatan" => "Statistisi Ahli Madya",
            "email" => "supandi@bps.go.id",
            "atasan_langsung_id" => "196908031992111001",
            "unit_kerja" => "BPS Kabupaten Mempawah"
        ]);
        // $pegawais = Pegawai::factory(20)->create();
    }
}
