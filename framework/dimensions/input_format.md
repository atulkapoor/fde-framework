---
id: input_format
type: enum
multi_valued: true
scope: functional
kind: requirement
weight: 2.0
asks: "What arrives, and in what form?"
ask_role: [admin, user, eval_owner]
values: [structured_data, documents, scanned_documents, text, images, streams, audio, video]
recognises:
  scanned_documents: [scanned, photographed, faxed, image of the document]
  documents: [pdfs, pdf, word documents, contracts, invoices, statements, reports, manuals, filings, policy document, submission documents, and documents, drawings, workpapers]
  structured_data: [from our database, csv, tables, warehouse, api responses, fault codes, meter data]
  text: [emails, tickets, chat logs, transcripts, free text, in-game chat, complaints]
  images: [photographs, photos, imagery, product images, camera feed, visual inspection, visual defect]
  streams: [events, telemetry, clickstream, sensor]
  audio: [by voice, voice calls, phone calls, call recordings, voicemail, spoken, audio recordings]
  video: [video of, video footage, camera footage, cctv, video feed, videos]
refines:
  scanned_documents: documents
  images: documents
---
Caps everything downstream, and is the most under-invested decision in most
systems. A badly parsed table is not recovered by a better model.

Scanned documents are a different problem from documents that happen to be
PDFs: one has a text layer and the other has pixels, and confusing them is how a
project discovers in week six that its ceiling was set in week one.
