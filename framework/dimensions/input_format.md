---
id: input_format
type: enum
scope: functional
kind: requirement
weight: 2.0
asks: "What arrives, and in what form?"
ask_role: [admin, user, eval_owner]
values: [structured_data, documents, scanned_documents, text, images, streams]
recognises:
  scanned_documents: [scanned, photographed, faxed, image of the document]
  documents: [pdfs, pdf, word documents, contracts, invoices, statements, reports, manuals, filings, policy document, submission documents]
  structured_data: [from our database, csv, tables, warehouse, api responses]
  text: [emails, tickets, chat logs, transcripts, free text]
  images: [photographs, photos, imagery, product images, camera feed, visual inspection, visual defect]
  streams: [events, telemetry, clickstream, sensor]
refines:
  scanned_documents: documents
  images: documents
---
Caps everything downstream, and is the most under-invested decision in most
systems. A badly parsed table is not recovered by a better model.

Scanned documents are a different problem from documents that happen to be
PDFs: one has a text layer and the other has pixels, and confusing them is how a
project discovers in week six that its ceiling was set in week one.
