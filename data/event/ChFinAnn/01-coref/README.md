# A Simple Coreference Resolution

Before tranforming document-level event records to sentence-level entity and relations,
we apply a regular expression for resolving one commonly encountered coreference
in the dataset, namely, abbreviation of company (organization) names.
The target is to spot more annotation spans which may make the entity relation 
model easier to learn: it helps reducing false negative rates due to unnormalized company names.
The regular expression is obtained by inspecting data samples
(which enjoy a common writing style of financial announcements).
