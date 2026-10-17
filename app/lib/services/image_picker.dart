import 'dart:typed_data';

import 'package:file_selector/file_selector.dart';

/// A reference image chosen by the author (bytes + original file name).
class PickedImage {
  final Uint8List bytes;
  final String name;
  const PickedImage(this.bytes, this.name);
}

typedef ImagePickerFn = Future<PickedImage?> Function();

/// Max upload size accepted by the backend (POST …/references).
const maxReferenceBytes = 8 << 20;

/// Opens the system file dialog for a PNG/JPEG (macOS needs the
/// `files.user-selected.read-only` entitlement).
Future<PickedImage?> pickImageFile() async {
  const group = XTypeGroup(
    label: 'Obrázky',
    extensions: ['png', 'jpg', 'jpeg'],
    mimeTypes: ['image/png', 'image/jpeg'],
    uniformTypeIdentifiers: ['public.png', 'public.jpeg'],
  );
  final file = await openFile(acceptedTypeGroups: const [group]);
  if (file == null) return null;
  return PickedImage(await file.readAsBytes(), file.name);
}
