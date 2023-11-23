# Reading the eDNA dataset

    library(dplyr)
    library(stringr)
    library(purrr)

    dna_files <- list.files("../output", "*DNADerivedData*", full.names = TRUE)
    occurrence_files <- list.files("../output", "*Occurrence*", full.names = TRUE)

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

    library(worrms)
    library(furrr)

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

    occurrence <- occurrence %>%
      mutate(verbatimScientificName = scientificName) %>%
      left_join(aphiaid_mapping, by = "aphiaid") %>%
      rows_update(valid_taxa, by = "valid_aphiaid") %>%
      mutate(
        species = ifelse(taxonRank == "species", scientificName, NA),
        aphiaid = as.numeric(str_replace(scientificNameID, "urn:lsid:marinespecies.org:taxname:", ""))
      ) %>%
      select(-valid_aphiaid)

Inspect updated names:

    occurrence %>%
      filter(scientificName != verbatimScientificName) %>%
      group_by(scientificName, verbatimScientificName) %>%
      summarize(n = n()) %>%
      arrange(desc(n)) %>%
      knitr::kable()

<table>
<colgroup>
<col style="width: 51%" />
<col style="width: 40%" />
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
<td style="text-align: right;">169901</td>
</tr>
<tr class="even">
<td style="text-align: left;">Harengula jaguana</td>
<td style="text-align: left;">Harengula humeralis</td>
<td style="text-align: right;">247</td>
</tr>
<tr class="odd">
<td style="text-align: left;">Azurina atrilobata</td>
<td style="text-align: left;">Chromis atrilobata</td>
<td style="text-align: right;">243</td>
</tr>
<tr class="even">
<td style="text-align: left;">Istiblennius edentulus</td>
<td style="text-align: left;">Istiblennius enosimae</td>
<td style="text-align: right;">101</td>
</tr>
<tr class="odd">
<td style="text-align: left;">Stegastes lacrymatus</td>
<td style="text-align: left;">Plectroglyphidodon lacrymatus</td>
<td style="text-align: right;">82</td>
</tr>
<tr class="even">
<td style="text-align: left;">Oblada melanurus</td>
<td style="text-align: left;">Oblada melanura</td>
<td style="text-align: right;">67</td>
</tr>
<tr class="odd">
<td style="text-align: left;">Hypoatherina temminckii</td>
<td style="text-align: left;">Hypoatherina gobio</td>
<td style="text-align: right;">57</td>
</tr>
<tr class="even">
<td style="text-align: left;">Plectroglyphidodon fasciolatus</td>
<td style="text-align: left;">Stegastes fasciolatus</td>
<td style="text-align: right;">46</td>
</tr>
<tr class="odd">
<td style="text-align: left;">Otolithoides pama</td>
<td style="text-align: left;">Pama pama</td>
<td style="text-align: right;">42</td>
</tr>
<tr class="even">
<td style="text-align: left;">Platybelone argalus</td>
<td style="text-align: left;">Platybelone argala</td>
<td style="text-align: right;">39</td>
</tr>
<tr class="odd">
<td style="text-align: left;">Plectroglyphidodon altus</td>
<td style="text-align: left;">Stegastes altus</td>
<td style="text-align: right;">29</td>
</tr>
<tr class="even">
<td style="text-align: left;">Pycnochromis vanderbilti</td>
<td style="text-align: left;">Chromis vanderbilti</td>
<td style="text-align: right;">27</td>
</tr>
<tr class="odd">
<td style="text-align: left;">Mugil cephalus</td>
<td style="text-align: left;">Mugil ashanteensis</td>
<td style="text-align: right;">24</td>
</tr>
<tr class="even">
<td style="text-align: left;">Osteomugil cunnesius</td>
<td style="text-align: left;">Moolgarda cunnesius</td>
<td style="text-align: right;">24</td>
</tr>
<tr class="odd">
<td style="text-align: left;">Siganus rivulatus</td>
<td style="text-align: left;">Scarus rivulatus</td>
<td style="text-align: right;">22</td>
</tr>
<tr class="even">
<td style="text-align: left;">Spratelloides gracilis</td>
<td style="text-align: left;">Spratelloides atrofasciatus</td>
<td style="text-align: right;">22</td>
</tr>
<tr class="odd">
<td style="text-align: left;">Yuopisthonema</td>
<td style="text-align: left;">Opisthonema</td>
<td style="text-align: right;">21</td>
</tr>
<tr class="even">
<td style="text-align: left;">Trachinotus blochii</td>
<td style="text-align: left;">Trachinotus falcatus</td>
<td style="text-align: right;">20</td>
</tr>
<tr class="odd">
<td style="text-align: left;">Mugil curema</td>
<td style="text-align: left;">Mugil metzelaari</td>
<td style="text-align: right;">19</td>
</tr>
<tr class="even">
<td style="text-align: left;">Taeniurops meyeni</td>
<td style="text-align: left;">Taeniura meyeni</td>
<td style="text-align: right;">17</td>
</tr>
<tr class="odd">
<td style="text-align: left;">Eleotris acanthopomus</td>
<td style="text-align: left;">Eleotris acanthopoma</td>
<td style="text-align: right;">16</td>
</tr>
<tr class="even">
<td style="text-align: left;">Arcticidae</td>
<td style="text-align: left;">Cyprinidae</td>
<td style="text-align: right;">14</td>
</tr>
<tr class="odd">
<td style="text-align: left;">Sardinops sagax</td>
<td style="text-align: left;">Sardinops melanostictus</td>
<td style="text-align: right;">14</td>
</tr>
<tr class="even">
<td style="text-align: left;">Helotes sexlineatus</td>
<td style="text-align: left;">Pelates sexlineatus</td>
<td style="text-align: right;">13</td>
</tr>
<tr class="odd">
<td style="text-align: left;">Planiliza planiceps</td>
<td style="text-align: left;">Chelon planiceps</td>
<td style="text-align: right;">13</td>
</tr>
<tr class="even">
<td style="text-align: left;">Callyspongia (Cladochalina) aculeata</td>
<td style="text-align: left;">Callyspongia vaginalis</td>
<td style="text-align: right;">12</td>
</tr>
<tr class="odd">
<td style="text-align: left;">Caranx ruber</td>
<td style="text-align: left;">Carangoides ruber</td>
<td style="text-align: right;">12</td>
</tr>
<tr class="even">
<td style="text-align: left;">Acanthostracion polygonium</td>
<td style="text-align: left;">Acanthostracion polygonius</td>
<td style="text-align: right;">11</td>
</tr>
<tr class="odd">
<td style="text-align: left;">Crenimugil pedaraki</td>
<td style="text-align: left;">Moolgarda pedaraki</td>
<td style="text-align: right;">8</td>
</tr>
<tr class="even">
<td style="text-align: left;">Maculabatis gerrardi</td>
<td style="text-align: left;">Himantura gerrardi</td>
<td style="text-align: right;">8</td>
</tr>
<tr class="odd">
<td style="text-align: left;">Pycnochromis margaritifer</td>
<td style="text-align: left;">Chromis margaritifer</td>
<td style="text-align: right;">8</td>
</tr>
<tr class="even">
<td style="text-align: left;">Dichotomyctere nigroviridis</td>
<td style="text-align: left;">Tetraodon nigroviridis</td>
<td style="text-align: right;">7</td>
</tr>
<tr class="odd">
<td style="text-align: left;">Enneanectes jordani</td>
<td style="text-align: left;">Enneanectes pectoralis</td>
<td style="text-align: right;">7</td>
</tr>
<tr class="even">
<td style="text-align: left;">Nanostrea pinnicola</td>
<td style="text-align: left;">Nanostrea fluctigera</td>
<td style="text-align: right;">7</td>
</tr>
<tr class="odd">
<td style="text-align: left;">Plectroglyphidodon gascoynei</td>
<td style="text-align: left;">Stegastes gascoynei</td>
<td style="text-align: right;">7</td>
</tr>
<tr class="even">
<td style="text-align: left;">Pycnochromis amboinensis</td>
<td style="text-align: left;">Chromis amboinensis</td>
<td style="text-align: right;">7</td>
</tr>
<tr class="odd">
<td style="text-align: left;">Sorsogona portuguesa</td>
<td style="text-align: left;">Rogadius portuguesus</td>
<td style="text-align: right;">7</td>
</tr>
<tr class="even">
<td style="text-align: left;">Crenimugil</td>
<td style="text-align: left;">Moolgarda</td>
<td style="text-align: right;">6</td>
</tr>
<tr class="odd">
<td style="text-align: left;">Eleotris fusca</td>
<td style="text-align: left;">Eleotris klunzingerii</td>
<td style="text-align: right;">6</td>
</tr>
<tr class="even">
<td style="text-align: left;">Ophiothrix (Ophiothrix) trilineata</td>
<td style="text-align: left;">Ophiothrix trilineata</td>
<td style="text-align: right;">6</td>
</tr>
<tr class="odd">
<td style="text-align: left;">Doboatherina aetholepis</td>
<td style="text-align: left;">Atherinomorus aetholepis</td>
<td style="text-align: right;">5</td>
</tr>
<tr class="even">
<td style="text-align: left;">Azurina cyanea</td>
<td style="text-align: left;">Chromis cyanea</td>
<td style="text-align: right;">4</td>
</tr>
<tr class="odd">
<td style="text-align: left;">Eucampia striata</td>
<td style="text-align: left;">Guinardia striata</td>
<td style="text-align: right;">4</td>
</tr>
<tr class="even">
<td style="text-align: left;">Acentrogobius nebulosus</td>
<td style="text-align: left;">Yongeichthys nebulosus</td>
<td style="text-align: right;">3</td>
</tr>
<tr class="odd">
<td style="text-align: left;">Ambassis ambassis</td>
<td style="text-align: left;">Ambassis commersoni</td>
<td style="text-align: right;">3</td>
</tr>
<tr class="even">
<td style="text-align: left;">Azurina lepidolepis</td>
<td style="text-align: left;">Chromis lepidolepis</td>
<td style="text-align: right;">3</td>
</tr>
<tr class="odd">
<td style="text-align: left;">Callyspongia (Callyspongia) fallax</td>
<td style="text-align: left;">Callyspongia fallax</td>
<td style="text-align: right;">3</td>
</tr>
<tr class="even">
<td style="text-align: left;">Coscinodiscus curvatulus var.
curvatulus</td>
<td style="text-align: left;">Actinocyclus curvatulus</td>
<td style="text-align: right;">3</td>
</tr>
<tr class="odd">
<td style="text-align: left;">Cubiceps whiteleggii</td>
<td style="text-align: left;">Cubiceps squamiceps</td>
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
<td style="text-align: left;">Oxyurichthys auchenolepis</td>
<td style="text-align: left;">Oxyurichthys saru</td>
<td style="text-align: right;">3</td>
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
<td style="text-align: left;">Heterocentrotus mamillatus</td>
<td style="text-align: left;">Heterocentrotus mammillatus</td>
<td style="text-align: right;">2</td>
</tr>
<tr class="odd">
<td style="text-align: left;">Holothuria (Halodeima) mexicana</td>
<td style="text-align: left;">Holothuria mexicana</td>
<td style="text-align: right;">2</td>
</tr>
<tr class="even">
<td style="text-align: left;">Mobula tarapacana</td>
<td style="text-align: left;">Mobula formosana</td>
<td style="text-align: right;">2</td>
</tr>
<tr class="odd">
<td style="text-align: left;">Ophiothrix (Ophiothrix) angulata</td>
<td style="text-align: left;">Ophiothrix angulata</td>
<td style="text-align: right;">2</td>
</tr>
<tr class="even">
<td style="text-align: left;">Pastinachus ater</td>
<td style="text-align: left;">Pastinachus atrus</td>
<td style="text-align: right;">2</td>
</tr>
<tr class="odd">
<td style="text-align: left;">Pycnochromis dimidiatus</td>
<td style="text-align: left;">Chromis dimidiata</td>
<td style="text-align: right;">2</td>
</tr>
<tr class="even">
<td style="text-align: left;">Sciades</td>
<td style="text-align: left;">Ariopsis</td>
<td style="text-align: right;">2</td>
</tr>
<tr class="odd">
<td style="text-align: left;">Sundstroemia setigera</td>
<td style="text-align: left;">Rhizosolenia setigera</td>
<td style="text-align: right;">2</td>
</tr>
<tr class="even">
<td style="text-align: left;">Uropterygius xanthopterus</td>
<td style="text-align: left;">Uropterygius alboguttatus</td>
<td style="text-align: right;">2</td>
</tr>
<tr class="odd">
<td style="text-align: left;">Asterorhombus cocosensis</td>
<td style="text-align: left;">Asterorhombus fijiensis</td>
<td style="text-align: right;">1</td>
</tr>
<tr class="even">
<td style="text-align: left;">Bellerochea polymorpha</td>
<td style="text-align: left;">Minutocellus polymorphus</td>
<td style="text-align: right;">1</td>
</tr>
<tr class="odd">
<td style="text-align: left;">Gymnothorax rueppelliae</td>
<td style="text-align: left;">Gymnothorax rueppellii</td>
<td style="text-align: right;">1</td>
</tr>
<tr class="even">
<td style="text-align: left;">Haliotis varia</td>
<td style="text-align: left;">Haliotis dohrniana</td>
<td style="text-align: right;">1</td>
</tr>
<tr class="odd">
<td style="text-align: left;">Holothuria (Stauropora) pervicax</td>
<td style="text-align: left;">Holothuria pervicax</td>
<td style="text-align: right;">1</td>
</tr>
<tr class="even">
<td style="text-align: left;">Holothuria (Thymiosycia) impatiens</td>
<td style="text-align: left;">Holothuria impatiens</td>
<td style="text-align: right;">1</td>
</tr>
<tr class="odd">
<td style="text-align: left;">Pycnochromis atripes</td>
<td style="text-align: left;">Chromis atripes</td>
<td style="text-align: right;">1</td>
</tr>
<tr class="even">
<td style="text-align: left;">Pycnochromis iomelas</td>
<td style="text-align: left;">Chromis iomelas</td>
<td style="text-align: right;">1</td>
</tr>
<tr class="odd">
<td style="text-align: left;">Pycnochromis nigrurus</td>
<td style="text-align: left;">Chromis nigrura</td>
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
<td style="text-align: left;">Xenojulis margaritacea</td>
<td style="text-align: left;">Xenojulis margaritaceus</td>
<td style="text-align: right;">1</td>
</tr>
</tbody>
</table>
