# Reading the eDNA dataset

Read the individual Occurrence and DNADerivedData files, and join them:

    library(dplyr)
    library(stringr)
    library(purrr)

    dna_files <- list.files("./data", "*DNADerivedData*", full.names = TRUE)
    occurrence_files <- list.files("./data", "*Occurrence*", full.names = TRUE)

    dna <- map(dna_files, read.table, sep = "\t", quote = "", header = TRUE) %>%
      bind_rows() %>%
      mutate_if(is.character, na_if, "")

    occurrence <- map(occurrence_files, read.table, sep = "\t", quote = "", header = TRUE) %>%
      bind_rows() %>%
      mutate_if(is.character, na_if, "") %>%
      mutate(
        species = ifelse(taxonRank == "species", scientificName, NA),
        aphiaid = as.numeric(str_replace(scientificNameID, "urn:lsid:marinespecies.org:taxname:", ""))
      ) %>%
      left_join(dna, by = "occurrenceID")

## Resolving to accepted species

The PacMAN pipeline aligns taxa with WoRMS, but this may included
unaccepted taxa such as synonyms. Use the procedure below to resolve all
taxa to their accepted names:

    library(worrms)
    library(furrr)

    resolve_to_accepted <- function(occurrence) {
      aphiaids <- unique(occurrence$aphiaid)
      aphiaid_batches <- split(aphiaids, as.integer((seq_along(aphiaids) - 1) / 50))
      plan(multisession, workers = 3)
      aphiaid_mapping <- future_map(aphiaid_batches, wm_record) %>%
        bind_rows() %>%
        select(aphiaid = AphiaID, valid_aphiaid = valid_AphiaID) %>%
        distinct() %>%
        filter(aphiaid != valid_aphiaid)
      
      valid_aphiaids <- unique(aphiaid_mapping$valid_aphiaid)
      valid_aphiaid_batches <- split(valid_aphiaids, as.integer((seq_along(valid_aphiaids) - 1) / 50))
      valid_taxa <- map(valid_aphiaid_batches, wm_record) %>%
        bind_rows() %>%
        select(valid_aphiaid = AphiaID, scientificName = scientificname, scientificNameID = lsid, taxonRank = rank, kingdom, phylum, class, order, family, genus) %>%
        mutate(taxonRank = tolower(taxonRank))
    occurrence %>%
      mutate(verbatimScientificName = scientificName) %>%
      left_join(aphiaid_mapping, by = "aphiaid") %>%
      rows_update(valid_taxa, by = "valid_aphiaid") %>%
      mutate(
        species = ifelse(taxonRank == "species", scientificName, NA),
        aphiaid = as.numeric(str_replace(scientificNameID, "urn:lsid:marinespecies.org:taxname:", ""))
      ) %>%
      select(-valid_aphiaid)
    }

    occurrence <- resolve_to_accepted(occurrence)

Inspect updated names:

    occurrence %>%
      filter(scientificName != verbatimScientificName) %>%
      group_by(scientificName, verbatimScientificName) %>%
      summarize(n = n()) %>%
      arrange(desc(n)) %>%
      knitr::kable()

<table>
<colgroup>
<col style="width: 54%" />
<col style="width: 37%" />
<col style="width: 8%" />
</colgroup>
<thead>
<tr class="header">
<th style="text-align: left;">scientificName</th>
<th style="text-align: left;">verbatimScientificName</th>
<th style="text-align: right;">n</th>
</tr>
</thead>
<tbody>
<tr class="odd">
<td style="text-align: left;">Animalia</td>
<td style="text-align: left;">Metazoa</td>
<td style="text-align: right;">293593</td>
</tr>
<tr class="even">
<td style="text-align: left;">Bellerochea polymorpha</td>
<td style="text-align: left;">Minutocellus polymorphus</td>
<td style="text-align: right;">858</td>
</tr>
<tr class="odd">
<td style="text-align: left;">Callyspongia (Cladochalina) plicifera</td>
<td style="text-align: left;">Callyspongia plicifera</td>
<td style="text-align: right;">493</td>
</tr>
<tr class="even">
<td style="text-align: left;">Neoparamoeba aestuarina</td>
<td style="text-align: left;">Paramoeba aestuarina</td>
<td style="text-align: right;">315</td>
</tr>
<tr class="odd">
<td style="text-align: left;">Azurina atrilobata</td>
<td style="text-align: left;">Chromis atrilobata</td>
<td style="text-align: right;">260</td>
</tr>
<tr class="even">
<td style="text-align: left;">Coscinodiscophycidae</td>
<td style="text-align: left;">Coscinodiscophyceae</td>
<td style="text-align: right;">226</td>
</tr>
<tr class="odd">
<td style="text-align: left;">Platybelone argalus</td>
<td style="text-align: left;">Platybelone argala</td>
<td style="text-align: right;">203</td>
</tr>
<tr class="even">
<td style="text-align: left;">Acartia (Acanthacartia) tonsa</td>
<td style="text-align: left;">Acartia tonsa</td>
<td style="text-align: right;">160</td>
</tr>
<tr class="odd">
<td style="text-align: left;">Eucampia striata</td>
<td style="text-align: left;">Guinardia striata</td>
<td style="text-align: right;">143</td>
</tr>
<tr class="even">
<td style="text-align: left;">Sundstroemia setigera</td>
<td style="text-align: left;">Rhizosolenia setigera</td>
<td style="text-align: right;">137</td>
</tr>
<tr class="odd">
<td style="text-align: left;">Clathria (Clathria) unica</td>
<td style="text-align: left;">Clathria unica</td>
<td style="text-align: right;">132</td>
</tr>
<tr class="even">
<td style="text-align: left;">Istiblennius edentulus</td>
<td style="text-align: left;">Istiblennius enosimae</td>
<td style="text-align: right;">127</td>
</tr>
<tr class="odd">
<td style="text-align: left;">Schizonema cruciger f. cruciger</td>
<td style="text-align: left;">Haslea crucigera</td>
<td style="text-align: right;">124</td>
</tr>
<tr class="even">
<td style="text-align: left;">Callyspongia (Callyspongia) fallax</td>
<td style="text-align: left;">Callyspongia fallax</td>
<td style="text-align: right;">121</td>
</tr>
<tr class="odd">
<td style="text-align: left;">Octactis octonaria</td>
<td style="text-align: left;">Dictyocha octonaria</td>
<td style="text-align: right;">115</td>
</tr>
<tr class="even">
<td style="text-align: left;">Octactis speculum</td>
<td style="text-align: left;">Dictyocha speculum</td>
<td style="text-align: right;">114</td>
</tr>
<tr class="odd">
<td style="text-align: left;">Ethmodiscus punctiger</td>
<td style="text-align: left;">Thalassiosira punctigera</td>
<td style="text-align: right;">112</td>
</tr>
<tr class="even">
<td style="text-align: left;">Plectroglyphidodon gascoynei</td>
<td style="text-align: left;">Stegastes gascoynei</td>
<td style="text-align: right;">111</td>
</tr>
<tr class="odd">
<td style="text-align: left;">Clathria (Wilsonella) rugosa</td>
<td style="text-align: left;">Clathria rugosa</td>
<td style="text-align: right;">110</td>
</tr>
<tr class="even">
<td style="text-align: left;">Paracartia grani grani</td>
<td style="text-align: left;">Paracartia grani</td>
<td style="text-align: right;">101</td>
</tr>
<tr class="odd">
<td style="text-align: left;">Hypoatherina temminckii</td>
<td style="text-align: left;">Hypoatherina gobio</td>
<td style="text-align: right;">97</td>
</tr>
<tr class="even">
<td style="text-align: left;">Stegastes lacrymatus</td>
<td style="text-align: left;">Plectroglyphidodon lacrymatus</td>
<td style="text-align: right;">95</td>
</tr>
<tr class="odd">
<td style="text-align: left;">Pentactella</td>
<td style="text-align: left;">Laevocnus</td>
<td style="text-align: right;">87</td>
</tr>
<tr class="even">
<td style="text-align: left;">Octocorallia</td>
<td style="text-align: left;">Alcyonacea</td>
<td style="text-align: right;">83</td>
</tr>
<tr class="odd">
<td style="text-align: left;">Oblada melanurus</td>
<td style="text-align: left;">Oblada melanura</td>
<td style="text-align: right;">72</td>
</tr>
<tr class="even">
<td style="text-align: left;">Paracalanus aculeatus aculeatus</td>
<td style="text-align: left;">Paracalanus aculeatus</td>
<td style="text-align: right;">58</td>
</tr>
<tr class="odd">
<td style="text-align: left;">Plectroglyphidodon fasciolatus</td>
<td style="text-align: left;">Stegastes fasciolatus</td>
<td style="text-align: right;">53</td>
</tr>
<tr class="even">
<td style="text-align: left;">Mugil cephalus</td>
<td style="text-align: left;">Mugil ashanteensis</td>
<td style="text-align: right;">47</td>
</tr>
<tr class="odd">
<td style="text-align: left;">Mycale (Carmia) cecilia</td>
<td style="text-align: left;">Mycale cecilia</td>
<td style="text-align: right;">47</td>
</tr>
<tr class="even">
<td style="text-align: left;">Osteomugil cunnesius</td>
<td style="text-align: left;">Moolgarda cunnesius</td>
<td style="text-align: right;">47</td>
</tr>
<tr class="odd">
<td style="text-align: left;">Callyspongia (Cladochalina) diffusa</td>
<td style="text-align: left;">Callyspongia diffusa</td>
<td style="text-align: right;">46</td>
</tr>
<tr class="even">
<td style="text-align: left;">Taeniurops meyeni</td>
<td style="text-align: left;">Taeniura meyeni</td>
<td style="text-align: right;">46</td>
</tr>
<tr class="odd">
<td style="text-align: left;">Cosmocalanus darwinii darwinii</td>
<td style="text-align: left;">Cosmocalanus darwinii</td>
<td style="text-align: right;">45</td>
</tr>
<tr class="even">
<td style="text-align: left;">Otolithoides pama</td>
<td style="text-align: left;">Pama pama</td>
<td style="text-align: right;">45</td>
</tr>
<tr class="odd">
<td style="text-align: left;">Sagartia lacerata</td>
<td style="text-align: left;">Sagartiogeton laceratus</td>
<td style="text-align: right;">43</td>
</tr>
<tr class="even">
<td style="text-align: left;">Haloa pemphis</td>
<td style="text-align: left;">Haminoea pemphis</td>
<td style="text-align: right;">42</td>
</tr>
<tr class="odd">
<td style="text-align: left;">Acartia (Acartia) negligens</td>
<td style="text-align: left;">Acartia negligens</td>
<td style="text-align: right;">39</td>
</tr>
<tr class="even">
<td style="text-align: left;">Cubiceps whiteleggii</td>
<td style="text-align: left;">Cubiceps squamiceps</td>
<td style="text-align: right;">38</td>
</tr>
<tr class="odd">
<td style="text-align: left;">Laurencia dendroidea</td>
<td style="text-align: left;">Laurencia majuscula</td>
<td style="text-align: right;">37</td>
</tr>
<tr class="even">
<td style="text-align: left;">Pycnochromis nigrurus</td>
<td style="text-align: left;">Chromis nigrura</td>
<td style="text-align: right;">37</td>
</tr>
<tr class="odd">
<td style="text-align: left;">Nicidion notata</td>
<td style="text-align: left;">Eunice notata</td>
<td style="text-align: right;">34</td>
</tr>
<tr class="even">
<td style="text-align: left;">Halichondria (Halichondria)
bowerbanki</td>
<td style="text-align: left;">Halichondria bowerbanki</td>
<td style="text-align: right;">33</td>
</tr>
<tr class="odd">
<td style="text-align: left;">Plectroglyphidodon altus</td>
<td style="text-align: left;">Stegastes altus</td>
<td style="text-align: right;">33</td>
</tr>
<tr class="even">
<td style="text-align: left;">Thecostraca</td>
<td style="text-align: left;">Hexanauplia</td>
<td style="text-align: right;">32</td>
</tr>
<tr class="odd">
<td style="text-align: left;">Pycnochromis vanderbilti</td>
<td style="text-align: left;">Chromis vanderbilti</td>
<td style="text-align: right;">27</td>
</tr>
<tr class="even">
<td style="text-align: left;">Callyspongia (Cladochalina) aculeata</td>
<td style="text-align: left;">Callyspongia vaginalis</td>
<td style="text-align: right;">26</td>
</tr>
<tr class="odd">
<td style="text-align: left;">Crella (Grayella) cyathophora</td>
<td style="text-align: left;">Crella cyathophora</td>
<td style="text-align: right;">26</td>
</tr>
<tr class="even">
<td style="text-align: left;">Leptastrea purpurea</td>
<td style="text-align: left;">Leptastrea pruinosa</td>
<td style="text-align: right;">26</td>
</tr>
<tr class="odd">
<td style="text-align: left;">Mugil curema</td>
<td style="text-align: left;">Mugil metzelaari</td>
<td style="text-align: right;">25</td>
</tr>
<tr class="even">
<td style="text-align: left;">Clathria (Thalysias) curacaoensis</td>
<td style="text-align: left;">Clathria curacaoensis</td>
<td style="text-align: right;">24</td>
</tr>
<tr class="odd">
<td style="text-align: left;">Crouania attenuata</td>
<td style="text-align: left;">Crouania minutissima</td>
<td style="text-align: right;">24</td>
</tr>
<tr class="even">
<td style="text-align: left;">Haliclona (Reniera) tubifera</td>
<td style="text-align: left;">Haliclona tubifera</td>
<td style="text-align: right;">24</td>
</tr>
<tr class="odd">
<td style="text-align: left;">Eleotris acanthopomus</td>
<td style="text-align: left;">Eleotris acanthopoma</td>
<td style="text-align: right;">23</td>
</tr>
<tr class="even">
<td style="text-align: left;">Navicula tsukamotoi</td>
<td style="text-align: left;">Haslea tsukamotoi</td>
<td style="text-align: right;">23</td>
</tr>
<tr class="odd">
<td style="text-align: left;">Hydropuntia perplexa</td>
<td style="text-align: left;">Gracilaria perplexa</td>
<td style="text-align: right;">22</td>
</tr>
<tr class="even">
<td style="text-align: left;">Kryptoperidinium triquetrum</td>
<td style="text-align: left;">Heterocapsa triquetra</td>
<td style="text-align: right;">22</td>
</tr>
<tr class="odd">
<td style="text-align: left;">Spratelloides gracilis</td>
<td style="text-align: left;">Spratelloides atrofasciatus</td>
<td style="text-align: right;">22</td>
</tr>
<tr class="even">
<td style="text-align: left;">Tedania (Tedania)</td>
<td style="text-align: left;">Tedania</td>
<td style="text-align: right;">22</td>
</tr>
<tr class="odd">
<td style="text-align: left;">Tedania (Tedania) tubulifera</td>
<td style="text-align: left;">Tedania tubulifera</td>
<td style="text-align: right;">22</td>
</tr>
<tr class="even">
<td style="text-align: left;">Acanthosiphonia echinata</td>
<td style="text-align: left;">Polysiphonia echinata</td>
<td style="text-align: right;">21</td>
</tr>
<tr class="odd">
<td style="text-align: left;">Amastigomonas debruynei</td>
<td style="text-align: left;">Thecamonas trahens</td>
<td style="text-align: right;">21</td>
</tr>
<tr class="even">
<td style="text-align: left;">Caranx ruber</td>
<td style="text-align: left;">Carangoides ruber</td>
<td style="text-align: right;">21</td>
</tr>
<tr class="odd">
<td style="text-align: left;">Diagramma pictum</td>
<td style="text-align: left;">Diagramma picta</td>
<td style="text-align: right;">21</td>
</tr>
<tr class="even">
<td style="text-align: left;">Lithophyllum prototypum</td>
<td style="text-align: left;">Titanoderma prototypum</td>
<td style="text-align: right;">21</td>
</tr>
<tr class="odd">
<td style="text-align: left;">Coscinodiscus curvatulus var.
curvatulus</td>
<td style="text-align: left;">Actinocyclus curvatulus</td>
<td style="text-align: right;">20</td>
</tr>
<tr class="even">
<td style="text-align: left;">Golfingia (Golfingia) elongata</td>
<td style="text-align: left;">Golfingia elongata</td>
<td style="text-align: right;">20</td>
</tr>
<tr class="odd">
<td style="text-align: left;">Haliclona (Halichoclona) vansoesti</td>
<td style="text-align: left;">Haliclona vansoesti</td>
<td style="text-align: right;">20</td>
</tr>
<tr class="even">
<td style="text-align: left;">Leptoscarus vaigiensis</td>
<td style="text-align: left;">Leptoscarus vaigienis</td>
<td style="text-align: right;">20</td>
</tr>
<tr class="odd">
<td style="text-align: left;">Tachidius (Tachidius) discipes</td>
<td style="text-align: left;">Tachidius discipes</td>
<td style="text-align: right;">19</td>
</tr>
<tr class="even">
<td style="text-align: left;">Holothuria (Thymiosycia) arenicola</td>
<td style="text-align: left;">Holothuria arenicola</td>
<td style="text-align: right;">18</td>
</tr>
<tr class="odd">
<td style="text-align: left;">Neoparamoeba pemaquidensis</td>
<td style="text-align: left;">Paramoeba pemaquidensis</td>
<td style="text-align: right;">18</td>
</tr>
<tr class="even">
<td style="text-align: left;">Aspidosiphon (Paraspidosiphon) laevis</td>
<td style="text-align: left;">Aspidosiphon laevis</td>
<td style="text-align: right;">17</td>
</tr>
<tr class="odd">
<td style="text-align: left;">Haliclona (Reniera) manglaris</td>
<td style="text-align: left;">Haliclona manglaris</td>
<td style="text-align: right;">17</td>
</tr>
<tr class="even">
<td style="text-align: left;">Helotes sexlineatus</td>
<td style="text-align: left;">Pelates sexlineatus</td>
<td style="text-align: right;">17</td>
</tr>
<tr class="odd">
<td style="text-align: left;">Hydroclathrus tilesii</td>
<td style="text-align: left;">Hydroclathrus stephanosorus</td>
<td style="text-align: right;">17</td>
</tr>
<tr class="even">
<td style="text-align: left;">Phascolosoma (Phascolosoma)
stephensoni</td>
<td style="text-align: left;">Phascolosoma stephensoni</td>
<td style="text-align: right;">17</td>
</tr>
<tr class="odd">
<td style="text-align: left;">Halichondria (Halichondria) okadai</td>
<td style="text-align: left;">Halichondria okadai</td>
<td style="text-align: right;">16</td>
</tr>
<tr class="even">
<td style="text-align: left;">Planiliza planiceps</td>
<td style="text-align: left;">Chelon planiceps</td>
<td style="text-align: right;">16</td>
</tr>
<tr class="odd">
<td style="text-align: left;">Sardinops sagax</td>
<td style="text-align: left;">Sardinops melanostictus</td>
<td style="text-align: right;">16</td>
</tr>
<tr class="even">
<td style="text-align: left;">Acanthostracion polygonium</td>
<td style="text-align: left;">Acanthostracion polygonius</td>
<td style="text-align: right;">15</td>
</tr>
<tr class="odd">
<td style="text-align: left;">Hypnea cervicornis</td>
<td style="text-align: left;">Hypnea flexicaulis</td>
<td style="text-align: right;">15</td>
</tr>
<tr class="even">
<td style="text-align: left;">Matsubaraea fusiformis</td>
<td style="text-align: left;">Matsubaraea fusiforme</td>
<td style="text-align: right;">15</td>
</tr>
<tr class="odd">
<td style="text-align: left;">Neogoniolithon brassica-florida</td>
<td style="text-align: left;">Neogoniolithon frutescens</td>
<td style="text-align: right;">15</td>
</tr>
<tr class="even">
<td style="text-align: left;">Omalacantha bicornuta</td>
<td style="text-align: left;">Microphrys bicornutus</td>
<td style="text-align: right;">15</td>
</tr>
<tr class="odd">
<td style="text-align: left;">Tortanus (Tortanus) forcipatus</td>
<td style="text-align: left;">Tortanus forcipatus</td>
<td style="text-align: right;">15</td>
</tr>
<tr class="even">
<td style="text-align: left;">Velamen parallelum</td>
<td style="text-align: left;">Vexillum parallelum</td>
<td style="text-align: right;">15</td>
</tr>
<tr class="odd">
<td style="text-align: left;">Cliothosa delitrix</td>
<td style="text-align: left;">Cliona delitrix</td>
<td style="text-align: right;">14</td>
</tr>
<tr class="even">
<td style="text-align: left;">Gnatholepis cauerensis</td>
<td style="text-align: left;">Gnatholepis scapulostigma</td>
<td style="text-align: right;">14</td>
</tr>
<tr class="odd">
<td style="text-align: left;">Halichondria (Halichondria) coerulea</td>
<td style="text-align: left;">Halichondria coerulea</td>
<td style="text-align: right;">14</td>
</tr>
<tr class="even">
<td style="text-align: left;">Lissodendoryx (Lissodendoryx)
carolinensis</td>
<td style="text-align: left;">Lissodendoryx carolinensis</td>
<td style="text-align: right;">14</td>
</tr>
<tr class="odd">
<td style="text-align: left;">Ophiothrix (Ophiothrix) trilineata</td>
<td style="text-align: left;">Ophiothrix trilineata</td>
<td style="text-align: right;">14</td>
</tr>
<tr class="even">
<td style="text-align: left;">Tedania (Tedania) ignis</td>
<td style="text-align: left;">Tedania ignis</td>
<td style="text-align: right;">14</td>
</tr>
<tr class="odd">
<td style="text-align: left;">Dondice occidentalis</td>
<td style="text-align: left;">Nanuca occidentalis</td>
<td style="text-align: right;">13</td>
</tr>
<tr class="even">
<td style="text-align: left;">Hecatonema terminale</td>
<td style="text-align: left;">Hecatonema maculans</td>
<td style="text-align: right;">13</td>
</tr>
<tr class="odd">
<td style="text-align: left;">Holothuria (Lessonothuria) lineata</td>
<td style="text-align: left;">Holothuria lineata</td>
<td style="text-align: right;">13</td>
</tr>
<tr class="even">
<td style="text-align: left;">Phascolosoma (Phascolosoma)
nigrescens</td>
<td style="text-align: left;">Phascolosoma nigrescens</td>
<td style="text-align: right;">13</td>
</tr>
<tr class="odd">
<td style="text-align: left;">Synedra minutissima var. pelliculosa</td>
<td style="text-align: left;">Fistulifera pelliculosa</td>
<td style="text-align: right;">13</td>
</tr>
<tr class="even">
<td style="text-align: left;">Balanodytes habei</td>
<td style="text-align: left;">Balanodytes taiwanus</td>
<td style="text-align: right;">12</td>
</tr>
<tr class="odd">
<td style="text-align: left;">Haliclona (Gellius) amboinensis</td>
<td style="text-align: left;">Haliclona amboinensis</td>
<td style="text-align: right;">12</td>
</tr>
<tr class="even">
<td style="text-align: left;">Macoma balthica</td>
<td style="text-align: left;">Limecola balthica</td>
<td style="text-align: right;">12</td>
</tr>
<tr class="odd">
<td style="text-align: left;">Microsiphona potamos</td>
<td style="text-align: left;">Skeletonema potamos</td>
<td style="text-align: right;">12</td>
</tr>
<tr class="even">
<td style="text-align: left;">Pycnochromis margaritifer</td>
<td style="text-align: left;">Chromis margaritifer</td>
<td style="text-align: right;">12</td>
</tr>
<tr class="odd">
<td style="text-align: left;">Acentrogobius nebulosus</td>
<td style="text-align: left;">Yongeichthys nebulosus</td>
<td style="text-align: right;">11</td>
</tr>
<tr class="even">
<td style="text-align: left;">Clytia brevithecata</td>
<td style="text-align: left;">Clytia hummelincki</td>
<td style="text-align: right;">11</td>
</tr>
<tr class="odd">
<td style="text-align: left;">Halichondria (Halichondria) panicea</td>
<td style="text-align: left;">Halichondria panicea</td>
<td style="text-align: right;">11</td>
</tr>
<tr class="even">
<td style="text-align: left;">Mycale (Carmia) fibrexilis</td>
<td style="text-align: left;">Mycale fibrexilis</td>
<td style="text-align: right;">11</td>
</tr>
<tr class="odd">
<td style="text-align: left;">Nanostrea pinnicola</td>
<td style="text-align: left;">Nanostrea fluctigera</td>
<td style="text-align: right;">11</td>
</tr>
<tr class="even">
<td style="text-align: left;">Nitzschia panduriformis
f. panduriformis</td>
<td style="text-align: left;">Psammodictyon panduriforme</td>
<td style="text-align: right;">11</td>
</tr>
<tr class="odd">
<td style="text-align: left;">Oithona simplex simplex</td>
<td style="text-align: left;">Oithona simplex</td>
<td style="text-align: right;">11</td>
</tr>
<tr class="even">
<td style="text-align: left;">Acartia (Acartiura) clausi</td>
<td style="text-align: left;">Acartia clausii</td>
<td style="text-align: right;">10</td>
</tr>
<tr class="odd">
<td style="text-align: left;">Crenimugil</td>
<td style="text-align: left;">Moolgarda</td>
<td style="text-align: right;">10</td>
</tr>
<tr class="even">
<td style="text-align: left;">Doboatherina aetholepis</td>
<td style="text-align: left;">Atherinomorus aetholepis</td>
<td style="text-align: right;">10</td>
</tr>
<tr class="odd">
<td style="text-align: left;">Gracilaria vermiculophylla</td>
<td style="text-align: left;">Agarophyton vermiculophyllum</td>
<td style="text-align: right;">10</td>
</tr>
<tr class="even">
<td style="text-align: left;">Melyvonnea erubescens</td>
<td style="text-align: left;">Mesophyllum erubescens</td>
<td style="text-align: right;">10</td>
</tr>
<tr class="odd">
<td style="text-align: left;">Uropterygius xanthopterus</td>
<td style="text-align: left;">Uropterygius alboguttatus</td>
<td style="text-align: right;">10</td>
</tr>
<tr class="even">
<td style="text-align: left;">Dichotomyctere nigroviridis</td>
<td style="text-align: left;">Tetraodon nigroviridis</td>
<td style="text-align: right;">9</td>
</tr>
<tr class="odd">
<td style="text-align: left;">Convolutidae</td>
<td style="text-align: left;">Sagittiferidae</td>
<td style="text-align: right;">8</td>
</tr>
<tr class="even">
<td style="text-align: left;">Holothuria (Halodeima) mexicana</td>
<td style="text-align: left;">Holothuria mexicana</td>
<td style="text-align: right;">8</td>
</tr>
<tr class="odd">
<td style="text-align: left;">Holothuria (Stauropora) pervicax</td>
<td style="text-align: left;">Holothuria pervicax</td>
<td style="text-align: right;">8</td>
</tr>
<tr class="even">
<td style="text-align: left;">Hydrolithon boergesenii</td>
<td style="text-align: left;">Hydrolithon reinboldii</td>
<td style="text-align: right;">8</td>
</tr>
<tr class="odd">
<td style="text-align: left;">Lanicola carus</td>
<td style="text-align: left;">Paraeupolymnia carus</td>
<td style="text-align: right;">8</td>
</tr>
<tr class="even">
<td style="text-align: left;">Lithophyllum okamurae</td>
<td style="text-align: left;">Lithophyllum validum</td>
<td style="text-align: right;">8</td>
</tr>
<tr class="odd">
<td style="text-align: left;">Maculabatis gerrardi</td>
<td style="text-align: left;">Himantura gerrardi</td>
<td style="text-align: right;">8</td>
</tr>
<tr class="even">
<td style="text-align: left;">Melanothamnus ramireziae</td>
<td style="text-align: left;">Neosiphonia ramireziae</td>
<td style="text-align: right;">8</td>
</tr>
<tr class="odd">
<td style="text-align: left;">Sorsogona portuguesa</td>
<td style="text-align: left;">Rogadius portuguesus</td>
<td style="text-align: right;">8</td>
</tr>
<tr class="even">
<td style="text-align: left;">Enneanectes jordani</td>
<td style="text-align: left;">Enneanectes pectoralis</td>
<td style="text-align: right;">7</td>
</tr>
<tr class="odd">
<td style="text-align: left;">Gymnothorax rueppelliae</td>
<td style="text-align: left;">Gymnothorax rueppellii</td>
<td style="text-align: right;">7</td>
</tr>
<tr class="even">
<td style="text-align: left;">Ophioderma cinereum</td>
<td style="text-align: left;">Ophioderma cinerea</td>
<td style="text-align: right;">7</td>
</tr>
<tr class="odd">
<td style="text-align: left;">Pycnochromis amboinensis</td>
<td style="text-align: left;">Chromis amboinensis</td>
<td style="text-align: right;">7</td>
</tr>
<tr class="even">
<td style="text-align: left;">Assiminea ovata</td>
<td style="text-align: left;">Assiminea capensis</td>
<td style="text-align: right;">6</td>
</tr>
<tr class="odd">
<td style="text-align: left;">Charybdis (Charybdis) annulata</td>
<td style="text-align: left;">Charybdis annulata</td>
<td style="text-align: right;">6</td>
</tr>
<tr class="even">
<td style="text-align: left;">Clathria (Clathria) pauper</td>
<td style="text-align: left;">Clathria pauper</td>
<td style="text-align: right;">6</td>
</tr>
<tr class="odd">
<td style="text-align: left;">Clathria (Clathria) prolifera</td>
<td style="text-align: left;">Clathria prolifera</td>
<td style="text-align: right;">6</td>
</tr>
<tr class="even">
<td style="text-align: left;">Eleotris fusca</td>
<td style="text-align: left;">Eleotris klunzingerii</td>
<td style="text-align: right;">6</td>
</tr>
<tr class="odd">
<td style="text-align: left;">Elysia velutinus</td>
<td style="text-align: left;">Elysia tuca</td>
<td style="text-align: right;">6</td>
</tr>
<tr class="even">
<td style="text-align: left;">Goniistius zebra</td>
<td style="text-align: left;">Cheilodactylus zebra</td>
<td style="text-align: right;">6</td>
</tr>
<tr class="odd">
<td style="text-align: left;">Haliclona (Reniera) implexiformis</td>
<td style="text-align: left;">Haliclona implexiformis</td>
<td style="text-align: right;">6</td>
</tr>
<tr class="even">
<td style="text-align: left;">Nereis splendida</td>
<td style="text-align: left;">Nereis falsa</td>
<td style="text-align: right;">6</td>
</tr>
<tr class="odd">
<td style="text-align: left;">Ophioderma appressum</td>
<td style="text-align: left;">Ophioderma appressa</td>
<td style="text-align: right;">6</td>
</tr>
<tr class="even">
<td style="text-align: left;">Ophiothrix (Ophiothrix) angulata</td>
<td style="text-align: left;">Ophiothrix angulata</td>
<td style="text-align: right;">6</td>
</tr>
<tr class="odd">
<td style="text-align: left;">Pareucalanus attenuatus</td>
<td style="text-align: left;">Eucalanus pseudattenuatus</td>
<td style="text-align: right;">6</td>
</tr>
<tr class="even">
<td style="text-align: left;">Watersipora cucullata</td>
<td style="text-align: left;">Watersipora subovoidea</td>
<td style="text-align: right;">6</td>
</tr>
<tr class="odd">
<td style="text-align: left;">Aspidosiphon (Akrikos) albus</td>
<td style="text-align: left;">Aspidosiphon albus</td>
<td style="text-align: right;">5</td>
</tr>
<tr class="even">
<td style="text-align: left;">Aspidosiphon (Aspidosiphon) gosnoldi</td>
<td style="text-align: left;">Aspidosiphon gosnoldi</td>
<td style="text-align: right;">5</td>
</tr>
<tr class="odd">
<td style="text-align: left;">Azurina cyanea</td>
<td style="text-align: left;">Chromis cyanea</td>
<td style="text-align: right;">5</td>
</tr>
<tr class="even">
<td style="text-align: left;">Charybdis (Charybdis) orientalis</td>
<td style="text-align: left;">Charybdis orientalis</td>
<td style="text-align: right;">5</td>
</tr>
<tr class="odd">
<td style="text-align: left;">Nemertea incertae sedis</td>
<td style="text-align: left;">Enopla</td>
<td style="text-align: right;">5</td>
</tr>
<tr class="even">
<td style="text-align: left;">Nephasoma (Nephasoma) pellucidum</td>
<td style="text-align: left;">Nephasoma pellucidum</td>
<td style="text-align: right;">5</td>
</tr>
<tr class="odd">
<td style="text-align: left;">Nicidion mutilata</td>
<td style="text-align: left;">Eunice mutilata</td>
<td style="text-align: right;">5</td>
</tr>
<tr class="even">
<td style="text-align: left;">Ophiothrix (Ophiothrix) oerstedii</td>
<td style="text-align: left;">Ophiothrix oerstedii</td>
<td style="text-align: right;">5</td>
</tr>
<tr class="odd">
<td style="text-align: left;">Pleonexes kava</td>
<td style="text-align: left;">Ampithoe kava</td>
<td style="text-align: right;">5</td>
</tr>
<tr class="even">
<td style="text-align: left;">Plocamium cartilagineum</td>
<td style="text-align: left;">Plocamium pusillum</td>
<td style="text-align: right;">5</td>
</tr>
<tr class="odd">
<td style="text-align: left;">Stephanocoenia intersepta</td>
<td style="text-align: left;">Stephanocoenia michelinii</td>
<td style="text-align: right;">5</td>
</tr>
<tr class="even">
<td style="text-align: left;">Amphiura (Amphiura) velox</td>
<td style="text-align: left;">Amphiura velox</td>
<td style="text-align: right;">4</td>
</tr>
<tr class="odd">
<td style="text-align: left;">Azurina lepidolepis</td>
<td style="text-align: left;">Chromis lepidolepis</td>
<td style="text-align: right;">4</td>
</tr>
<tr class="even">
<td style="text-align: left;">Caranx bartholomaei</td>
<td style="text-align: left;">Carangoides bartholomaei</td>
<td style="text-align: right;">4</td>
</tr>
<tr class="odd">
<td style="text-align: left;">Chaetopterus variopedatus</td>
<td style="text-align: left;">Chaetopterus longimanus</td>
<td style="text-align: right;">4</td>
</tr>
<tr class="even">
<td style="text-align: left;">Etrumeus sadina</td>
<td style="text-align: left;">Etrumeus teres</td>
<td style="text-align: right;">4</td>
</tr>
<tr class="odd">
<td style="text-align: left;">Ferdauia orthogrammus</td>
<td style="text-align: left;">Carangoides orthogrammus</td>
<td style="text-align: right;">4</td>
</tr>
<tr class="even">
<td style="text-align: left;">Hydropuntia edulis</td>
<td style="text-align: left;">Gracilaria edulis</td>
<td style="text-align: right;">4</td>
</tr>
<tr class="odd">
<td style="text-align: left;">Kyphosus vaigiensis</td>
<td style="text-align: left;">Kyphosus analogus</td>
<td style="text-align: right;">4</td>
</tr>
<tr class="even">
<td style="text-align: left;">Ophiothrix (Ophiothrix) spiculata</td>
<td style="text-align: left;">Ophiothrix spiculata</td>
<td style="text-align: right;">4</td>
</tr>
<tr class="odd">
<td style="text-align: left;">Pennatuloidea</td>
<td style="text-align: left;">Pennatulacea</td>
<td style="text-align: right;">4</td>
</tr>
<tr class="even">
<td style="text-align: left;">Phascolosoma (Phascolosoma) pacificum</td>
<td style="text-align: left;">Phascolosoma pacificum</td>
<td style="text-align: right;">4</td>
</tr>
<tr class="odd">
<td style="text-align: left;">Planes minutus</td>
<td style="text-align: left;">Planes major</td>
<td style="text-align: right;">4</td>
</tr>
<tr class="even">
<td style="text-align: left;">Pycnochromis dimidiatus</td>
<td style="text-align: left;">Chromis dimidiata</td>
<td style="text-align: right;">4</td>
</tr>
<tr class="odd">
<td style="text-align: left;">Rhizosolenia delicatula</td>
<td style="text-align: left;">Guinardia delicatula</td>
<td style="text-align: right;">4</td>
</tr>
<tr class="even">
<td style="text-align: left;">Sclerophytum penghuense</td>
<td style="text-align: left;">Sinularia penghuensis</td>
<td style="text-align: right;">4</td>
</tr>
<tr class="odd">
<td style="text-align: left;">Stomatia phymotis</td>
<td style="text-align: left;">Stomatia obscura</td>
<td style="text-align: right;">4</td>
</tr>
<tr class="even">
<td style="text-align: left;">Acartia (Acanthacartia) bifilosa</td>
<td style="text-align: left;">Acartia bifilosa</td>
<td style="text-align: right;">3</td>
</tr>
<tr class="odd">
<td style="text-align: left;">Ambassis ambassis</td>
<td style="text-align: left;">Ambassis commersoni</td>
<td style="text-align: right;">3</td>
</tr>
<tr class="even">
<td style="text-align: left;">Clathria (Thalysias) reinwardti</td>
<td style="text-align: left;">Clathria reinwardti</td>
<td style="text-align: right;">3</td>
</tr>
<tr class="odd">
<td style="text-align: left;">Creseis acicula</td>
<td style="text-align: left;">Creseis clava</td>
<td style="text-align: right;">3</td>
</tr>
<tr class="even">
<td style="text-align: left;">Encrasicholina heteroloba</td>
<td style="text-align: left;">Encrasicholina pseudoheteroloba</td>
<td style="text-align: right;">3</td>
</tr>
<tr class="odd">
<td style="text-align: left;">Epinephelus marginatus</td>
<td style="text-align: left;">Mycteroperca marginata</td>
<td style="text-align: right;">3</td>
</tr>
<tr class="even">
<td style="text-align: left;">Fundulus xenicus</td>
<td style="text-align: left;">Adinia xenica</td>
<td style="text-align: right;">3</td>
</tr>
<tr class="odd">
<td style="text-align: left;">Gnathostomula mediterranea</td>
<td style="text-align: left;">Gnathostomula axi</td>
<td style="text-align: right;">3</td>
</tr>
<tr class="even">
<td style="text-align: left;">Jania cultrata</td>
<td style="text-align: left;">Cheilosporum cultratum</td>
<td style="text-align: right;">3</td>
</tr>
<tr class="odd">
<td style="text-align: left;">Lamprohaminoea ovalis</td>
<td style="text-align: left;">Haminoea ovalis</td>
<td style="text-align: right;">3</td>
</tr>
<tr class="even">
<td style="text-align: left;">Larus ridibundus</td>
<td style="text-align: left;">Chroicocephalus ridibundus</td>
<td style="text-align: right;">3</td>
</tr>
<tr class="odd">
<td style="text-align: left;">Leodice miurai</td>
<td style="text-align: left;">Eunice miurai</td>
<td style="text-align: right;">3</td>
</tr>
<tr class="even">
<td style="text-align: left;">Leodice rubra</td>
<td style="text-align: left;">Eunice rubra</td>
<td style="text-align: right;">3</td>
</tr>
<tr class="odd">
<td style="text-align: left;">Lobophora canariensis</td>
<td style="text-align: left;">Lobophora payriae</td>
<td style="text-align: right;">3</td>
</tr>
<tr class="even">
<td style="text-align: left;">Macrophthalmus (Macrophthalmus)
milloti</td>
<td style="text-align: left;">Macrophthalmus milloti</td>
<td style="text-align: right;">3</td>
</tr>
<tr class="odd">
<td style="text-align: left;">Microspongium stilophorae</td>
<td style="text-align: left;">Microspongium tenuissimum</td>
<td style="text-align: right;">3</td>
</tr>
<tr class="even">
<td style="text-align: left;">Nicidion angeli</td>
<td style="text-align: left;">Marphysa angeli</td>
<td style="text-align: right;">3</td>
</tr>
<tr class="odd">
<td style="text-align: left;">Oxyurichthys auchenolepis</td>
<td style="text-align: left;">Oxyurichthys saru</td>
<td style="text-align: right;">3</td>
</tr>
<tr class="even">
<td style="text-align: left;">Petrosia (Petrosia) ficiformis</td>
<td style="text-align: left;">Petrosia ficiformis</td>
<td style="text-align: right;">3</td>
</tr>
<tr class="odd">
<td style="text-align: left;">Phascolosoma (Phascolosoma) perlucens</td>
<td style="text-align: left;">Phascolosoma perlucens</td>
<td style="text-align: right;">3</td>
</tr>
<tr class="even">
<td style="text-align: left;">Pycnochromis iomelas</td>
<td style="text-align: left;">Chromis iomelas</td>
<td style="text-align: right;">3</td>
</tr>
<tr class="odd">
<td style="text-align: left;">Sagmatias obliquidens</td>
<td style="text-align: left;">Lagenorhynchus obliquidens</td>
<td style="text-align: right;">3</td>
</tr>
<tr class="even">
<td style="text-align: left;">Sclerophytum grandilobatum</td>
<td style="text-align: left;">Sinularia grandilobata</td>
<td style="text-align: right;">3</td>
</tr>
<tr class="odd">
<td style="text-align: left;">Sclerophytum heterospiculatum</td>
<td style="text-align: left;">Sinularia heterospiculata</td>
<td style="text-align: right;">3</td>
</tr>
<tr class="even">
<td style="text-align: left;">Thalamita chaptalii</td>
<td style="text-align: left;">Thalamita chaptali</td>
<td style="text-align: right;">3</td>
</tr>
<tr class="odd">
<td style="text-align: left;">Tomoberthella martensi</td>
<td style="text-align: left;">Berthella martensi</td>
<td style="text-align: right;">3</td>
</tr>
<tr class="even">
<td style="text-align: left;">Watersipora subtorquata</td>
<td style="text-align: left;">Watersipora edmondsoni</td>
<td style="text-align: right;">3</td>
</tr>
<tr class="odd">
<td style="text-align: left;">Abantennarius coccineus</td>
<td style="text-align: left;">Antennatus coccineus</td>
<td style="text-align: right;">2</td>
</tr>
<tr class="even">
<td style="text-align: left;">Ambassis ambassis</td>
<td style="text-align: left;">Ambassis productus</td>
<td style="text-align: right;">2</td>
</tr>
<tr class="odd">
<td style="text-align: left;">Amphioplus (Lymanella) laevis</td>
<td style="text-align: left;">Amphioplus laevis</td>
<td style="text-align: right;">2</td>
</tr>
<tr class="even">
<td style="text-align: left;">Anomalocardia puella</td>
<td style="text-align: left;">Anomalocardia auberiana</td>
<td style="text-align: right;">2</td>
</tr>
<tr class="odd">
<td style="text-align: left;">Bacillariophyceae</td>
<td style="text-align: left;">Fragilariophyceae</td>
<td style="text-align: right;">2</td>
</tr>
<tr class="even">
<td style="text-align: left;">Callithamnion tetragonum</td>
<td style="text-align: left;">Callithamnion baileyi</td>
<td style="text-align: right;">2</td>
</tr>
<tr class="odd">
<td style="text-align: left;">Camachoaglaja mariagordae</td>
<td style="text-align: left;">Chelidonura normani</td>
<td style="text-align: right;">2</td>
</tr>
<tr class="even">
<td style="text-align: left;">Clathria (Thalysias) abietina</td>
<td style="text-align: left;">Clathria abietina</td>
<td style="text-align: right;">2</td>
</tr>
<tr class="odd">
<td style="text-align: left;">Corallina ferreyrae</td>
<td style="text-align: left;">Corallina caespitosa</td>
<td style="text-align: right;">2</td>
</tr>
<tr class="even">
<td style="text-align: left;">Corallinales</td>
<td style="text-align: left;">Hapalidiales</td>
<td style="text-align: right;">2</td>
</tr>
<tr class="odd">
<td style="text-align: left;">Crenimugil pedaraki</td>
<td style="text-align: left;">Moolgarda pedaraki</td>
<td style="text-align: right;">2</td>
</tr>
<tr class="even">
<td style="text-align: left;">Dasyscopelus spinosus</td>
<td style="text-align: left;">Myctophum spinosum</td>
<td style="text-align: right;">2</td>
</tr>
<tr class="odd">
<td style="text-align: left;">Dulcerana granularis</td>
<td style="text-align: left;">Bursa granularis</td>
<td style="text-align: right;">2</td>
</tr>
<tr class="even">
<td style="text-align: left;">Gasterosteus aculeatus</td>
<td style="text-align: left;">Gasterosteus gymnurus</td>
<td style="text-align: right;">2</td>
</tr>
<tr class="odd">
<td style="text-align: left;">Gracilaria fisheri</td>
<td style="text-align: left;">Hydropuntia fisheri</td>
<td style="text-align: right;">2</td>
</tr>
<tr class="even">
<td style="text-align: left;">Halichondria (Halichondria)
melanadocia</td>
<td style="text-align: left;">Halichondria melanadocia</td>
<td style="text-align: right;">2</td>
</tr>
<tr class="odd">
<td style="text-align: left;">Heterocentrotus mamillatus</td>
<td style="text-align: left;">Heterocentrotus mammillatus</td>
<td style="text-align: right;">2</td>
</tr>
<tr class="even">
<td style="text-align: left;">Holothuria (Holothuria) mammata</td>
<td style="text-align: left;">Holothuria mammata</td>
<td style="text-align: right;">2</td>
</tr>
<tr class="odd">
<td style="text-align: left;">Holothuria (Lessonothuria) pardalis</td>
<td style="text-align: left;">Holothuria pardalis</td>
<td style="text-align: right;">2</td>
</tr>
<tr class="even">
<td style="text-align: left;">Holothuria (Platyperona) difficilis</td>
<td style="text-align: left;">Holothuria difficilis</td>
<td style="text-align: right;">2</td>
</tr>
<tr class="odd">
<td style="text-align: left;">Holothuria (Thymiosycia) impatiens</td>
<td style="text-align: left;">Holothuria impatiens</td>
<td style="text-align: right;">2</td>
</tr>
<tr class="even">
<td style="text-align: left;">Hommersandiophycus pectinatus</td>
<td style="text-align: left;">Liagora pectinata</td>
<td style="text-align: right;">2</td>
</tr>
<tr class="odd">
<td style="text-align: left;">Hydropuntia eucheumatoides</td>
<td style="text-align: left;">Gracilaria eucheumatoides</td>
<td style="text-align: right;">2</td>
</tr>
<tr class="even">
<td style="text-align: left;">Jania prolifera</td>
<td style="text-align: left;">Cheilosporum proliferum</td>
<td style="text-align: right;">2</td>
</tr>
<tr class="odd">
<td style="text-align: left;">Kapraunia pentamera</td>
<td style="text-align: left;">Polysiphonia pentamera</td>
<td style="text-align: right;">2</td>
</tr>
<tr class="even">
<td style="text-align: left;">Lophocochlias parvissimus</td>
<td style="text-align: left;">Lophocochlias minutissimus</td>
<td style="text-align: right;">2</td>
</tr>
<tr class="odd">
<td style="text-align: left;">Marioniopsis hawaiiensis</td>
<td style="text-align: left;">Marionia hawaiiensis</td>
<td style="text-align: right;">2</td>
</tr>
<tr class="even">
<td style="text-align: left;">Mesocyclops (Mesocyclops) leuckarti
leuckarti</td>
<td style="text-align: left;">Mesocyclops leuckarti</td>
<td style="text-align: right;">2</td>
</tr>
<tr class="odd">
<td style="text-align: left;">Mobula tarapacana</td>
<td style="text-align: left;">Mobula formosana</td>
<td style="text-align: right;">2</td>
</tr>
<tr class="even">
<td style="text-align: left;">Neopetrosia chaliniformis</td>
<td style="text-align: left;">Neopetrosia exigua</td>
<td style="text-align: right;">2</td>
</tr>
<tr class="odd">
<td style="text-align: left;">Nicidion mikeli</td>
<td style="text-align: left;">Eunice mikeli</td>
<td style="text-align: right;">2</td>
</tr>
<tr class="even">
<td style="text-align: left;">Ophioderma longicaudum</td>
<td style="text-align: left;">Ophioderma longicauda</td>
<td style="text-align: right;">2</td>
</tr>
<tr class="odd">
<td style="text-align: left;">Paracalanus parvus parvus</td>
<td style="text-align: left;">Paracalanus parvus</td>
<td style="text-align: right;">2</td>
</tr>
<tr class="even">
<td style="text-align: left;">Sargocentron suborbitale</td>
<td style="text-align: left;">Sargocentron suborbitalis</td>
<td style="text-align: right;">2</td>
</tr>
<tr class="odd">
<td style="text-align: left;">Sciades</td>
<td style="text-align: left;">Ariopsis</td>
<td style="text-align: right;">2</td>
</tr>
<tr class="even">
<td style="text-align: left;">Sipunculus (Sipunculus) nudus</td>
<td style="text-align: left;">Sipunculus nudus</td>
<td style="text-align: right;">2</td>
</tr>
<tr class="odd">
<td style="text-align: left;">Subeucalanus subtenuis</td>
<td style="text-align: left;">Eucalanus subtenuis</td>
<td style="text-align: right;">2</td>
</tr>
<tr class="even">
<td style="text-align: left;">Syllis</td>
<td style="text-align: left;">Typosyllis</td>
<td style="text-align: right;">2</td>
</tr>
<tr class="odd">
<td style="text-align: left;">Thalamita crenata</td>
<td style="text-align: left;">Thranita crenata</td>
<td style="text-align: right;">2</td>
</tr>
<tr class="even">
<td style="text-align: left;">Triceratium alternans f. alternans</td>
<td style="text-align: left;">Biddulphia alternans</td>
<td style="text-align: right;">2</td>
</tr>
<tr class="odd">
<td style="text-align: left;">Trochus stellatus</td>
<td style="text-align: left;">Trochus incrassatus</td>
<td style="text-align: right;">2</td>
</tr>
<tr class="even">
<td style="text-align: left;">Abantennarius sanguineus</td>
<td style="text-align: left;">Antennatus sanguineus</td>
<td style="text-align: right;">1</td>
</tr>
<tr class="odd">
<td style="text-align: left;">Acanthocyclops vernalis vernalis</td>
<td style="text-align: left;">Acanthocyclops vernalis</td>
<td style="text-align: right;">1</td>
</tr>
<tr class="even">
<td style="text-align: left;">Acroteriobatus annulatus</td>
<td style="text-align: left;">Rhinobatos annulatus</td>
<td style="text-align: right;">1</td>
</tr>
<tr class="odd">
<td style="text-align: left;">Agathistoma fasciatum</td>
<td style="text-align: left;">Tegula fasciata</td>
<td style="text-align: right;">1</td>
</tr>
<tr class="even">
<td style="text-align: left;">Alcyoniidae</td>
<td style="text-align: left;">Anthothelidae</td>
<td style="text-align: right;">1</td>
</tr>
<tr class="odd">
<td style="text-align: left;">Apatizanclea divergens</td>
<td style="text-align: left;">Zanclea divergens</td>
<td style="text-align: right;">1</td>
</tr>
<tr class="even">
<td style="text-align: left;">Asterorhombus cocosensis</td>
<td style="text-align: left;">Asterorhombus fijiensis</td>
<td style="text-align: right;">1</td>
</tr>
<tr class="odd">
<td style="text-align: left;">Atys semistriatus</td>
<td style="text-align: left;">Atys semistriata</td>
<td style="text-align: right;">1</td>
</tr>
<tr class="even">
<td style="text-align: left;">Bunodactis verrucosa</td>
<td style="text-align: left;">Aulactinia verrucosa</td>
<td style="text-align: right;">1</td>
</tr>
<tr class="odd">
<td style="text-align: left;">Caphyra rotundifrons</td>
<td style="text-align: left;">Trierarchus rotundifrons</td>
<td style="text-align: right;">1</td>
</tr>
<tr class="even">
<td style="text-align: left;">Cephalotrichella alba</td>
<td style="text-align: left;">Cephalothrix alba</td>
<td style="text-align: right;">1</td>
</tr>
<tr class="odd">
<td style="text-align: left;">Chondria capillaris</td>
<td style="text-align: left;">Chondria tenuissima</td>
<td style="text-align: right;">1</td>
</tr>
<tr class="even">
<td style="text-align: left;">Deckertichthys aureolus</td>
<td style="text-align: left;">Diapterus aureolus</td>
<td style="text-align: right;">1</td>
</tr>
<tr class="odd">
<td style="text-align: left;">Dendostrea sandvichensis</td>
<td style="text-align: left;">Dendostrea crenulifera</td>
<td style="text-align: right;">1</td>
</tr>
<tr class="even">
<td style="text-align: left;">Fromia indica</td>
<td style="text-align: left;">Fromia elegans</td>
<td style="text-align: right;">1</td>
</tr>
<tr class="odd">
<td style="text-align: left;">Gymnogongrus durvillei</td>
<td style="text-align: left;">Ahnfeltiopsis concinna</td>
<td style="text-align: right;">1</td>
</tr>
<tr class="even">
<td style="text-align: left;">Haliotis varia</td>
<td style="text-align: left;">Haliotis dohrniana</td>
<td style="text-align: right;">1</td>
</tr>
<tr class="odd">
<td style="text-align: left;">Haloa aptei</td>
<td style="text-align: left;">Haminoea aptei</td>
<td style="text-align: right;">1</td>
</tr>
<tr class="even">
<td style="text-align: left;">Hansarsia gracilis</td>
<td style="text-align: left;">Nematoscelis gracilis</td>
<td style="text-align: right;">1</td>
</tr>
<tr class="odd">
<td style="text-align: left;">Idotea balthica</td>
<td style="text-align: left;">Idotea baltica</td>
<td style="text-align: right;">1</td>
</tr>
<tr class="even">
<td style="text-align: left;">Lampasopsis thomae</td>
<td style="text-align: left;">Bursa thomae</td>
<td style="text-align: right;">1</td>
</tr>
<tr class="odd">
<td style="text-align: left;">Lepas (Lepas) anserifera</td>
<td style="text-align: left;">Lepas anserifera</td>
<td style="text-align: right;">1</td>
</tr>
<tr class="even">
<td style="text-align: left;">Melanothamnus pseudovillum</td>
<td style="text-align: left;">Polysiphonia pseudovillum</td>
<td style="text-align: right;">1</td>
</tr>
<tr class="odd">
<td style="text-align: left;">Mierspenaeopsis sculptilis</td>
<td style="text-align: left;">Parapenaeopsis sculptilis</td>
<td style="text-align: right;">1</td>
</tr>
<tr class="even">
<td style="text-align: left;">Nephasoma (Nephasoma) rimicola</td>
<td style="text-align: left;">Nephasoma rimicola</td>
<td style="text-align: right;">1</td>
</tr>
<tr class="odd">
<td style="text-align: left;">Ophioderma panamense</td>
<td style="text-align: left;">Ophioderma panamensis</td>
<td style="text-align: right;">1</td>
</tr>
<tr class="even">
<td style="text-align: left;">Ophiopeza fallax fallax</td>
<td style="text-align: left;">Ophiopeza fallax</td>
<td style="text-align: right;">1</td>
</tr>
<tr class="odd">
<td style="text-align: left;">Ophiothrix (Acanthophiothrix)
suensonii</td>
<td style="text-align: left;">Ophiothrix suensoni</td>
<td style="text-align: right;">1</td>
</tr>
<tr class="even">
<td style="text-align: left;">Ophiothrix (Ophiothrix) echinotecta</td>
<td style="text-align: left;">Ophiothrix echinotecta</td>
<td style="text-align: right;">1</td>
</tr>
<tr class="odd">
<td style="text-align: left;">Ostracion cubicum</td>
<td style="text-align: left;">Ostracion cubicus</td>
<td style="text-align: right;">1</td>
</tr>
<tr class="even">
<td style="text-align: left;">Petromica (Chaladesma) pacifica</td>
<td style="text-align: left;">Petromica pacifica</td>
<td style="text-align: right;">1</td>
</tr>
<tr class="odd">
<td style="text-align: left;">Pictorium koperbergi</td>
<td style="text-align: left;">Cerithium koperbergi</td>
<td style="text-align: right;">1</td>
</tr>
<tr class="even">
<td style="text-align: left;">Platoma cyclocolpum</td>
<td style="text-align: left;">Platoma cyclocolpa</td>
<td style="text-align: right;">1</td>
</tr>
<tr class="odd">
<td style="text-align: left;">Plectorhinchus schotaf</td>
<td style="text-align: left;">Plectorhinchus unicolor</td>
<td style="text-align: right;">1</td>
</tr>
<tr class="even">
<td style="text-align: left;">Pycnochromis atripes</td>
<td style="text-align: left;">Chromis atripes</td>
<td style="text-align: right;">1</td>
</tr>
<tr class="odd">
<td style="text-align: left;">Saccostrea cuccullata</td>
<td style="text-align: left;">Saccostrea cucullata</td>
<td style="text-align: right;">1</td>
</tr>
<tr class="even">
<td style="text-align: left;">Serranus scriba</td>
<td style="text-align: left;">Serranus papilionaceus</td>
<td style="text-align: right;">1</td>
</tr>
<tr class="odd">
<td style="text-align: left;">Stercorarius antarcticus</td>
<td style="text-align: left;">Stercorarius lonnbergi</td>
<td style="text-align: right;">1</td>
</tr>
<tr class="even">
<td style="text-align: left;">Taeniurops grabatus</td>
<td style="text-align: left;">Taeniura grabata</td>
<td style="text-align: right;">1</td>
</tr>
<tr class="odd">
<td style="text-align: left;">Tetraclita squamosa</td>
<td style="text-align: left;">Tetraclita milleporosa</td>
<td style="text-align: right;">1</td>
</tr>
<tr class="even">
<td style="text-align: left;">Thalamita coeruleipes</td>
<td style="text-align: left;">Thranita coeruleipes</td>
<td style="text-align: right;">1</td>
</tr>
<tr class="odd">
<td style="text-align: left;">Thalamita pelsarti</td>
<td style="text-align: left;">Thranita pelsarti</td>
<td style="text-align: right;">1</td>
</tr>
<tr class="even">
<td style="text-align: left;">Themiste (Lagenopsis) lageniformis</td>
<td style="text-align: left;">Themiste lageniformis</td>
<td style="text-align: right;">1</td>
</tr>
<tr class="odd">
<td style="text-align: left;">Themiste (Lagenopsis) minor</td>
<td style="text-align: left;">Themiste minor</td>
<td style="text-align: right;">1</td>
</tr>
<tr class="even">
<td style="text-align: left;">Xenojulis margaritacea</td>
<td style="text-align: left;">Xenojulis margaritaceus</td>
<td style="text-align: right;">1</td>
</tr>
</tbody>
</table>
