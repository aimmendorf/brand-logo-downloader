# Brand Logo Downloader

A small Python script that downloads brand logo assets from the
[Brandfetch](https://brandfetch.com) API. For each brand it grabs every variant
Brandfetch offers — logo, symbol, and icon, in light and dark themes, across
whatever formats are available (SVG, PNG, WebP, JPEG) — and organizes them into
per-brand folders.

## Requirements

- Python 3.9+
- A free Brandfetch API key ([brandfetch.com/developers](https://brandfetch.com/developers))

## Setup

```bash
pip install requests python-dotenv
cp .env.example .env
```

Then open `.env` and add your key:

```
BRANDFETCH_API_KEY=your_key_here
BRANDFETCH_CLIENT_ID=your_client_id_here   # optional, only for name search
```

`.env` is git-ignored, so your key stays local.

## Choosing which brands to download

Brands are listed in a text file (default `brands.txt`). Copy the example to get
started:

```bash
cp brands.example.txt brands.txt
```

Each non-empty, non-`#` line is one brand, in any of these forms:

```
apple.com                    # bare domain  -> folder named "apple"
Procter & Gamble = pg.com    # custom name  -> exact domain
Starbucks                    # bare name    -> resolved via Brandfetch Search
```

`brands.txt` is git-ignored so you can keep your own list private.

## Usage

```bash
python download_brand_logos.py                    # read brands.txt
python download_brand_logos.py --file mylist.txt  # read a specific file
python download_brand_logos.py apple.com nike.com # brands straight from the CLI
python download_brand_logos.py "Coca-Cola = coca-cola.com"
```

## Output

Files are written to `logos/<brand>/` (git-ignored), named
`<brand>_<type>_<theme>.<ext>`, for example:

```
logos/
  apple/
    apple_logo_dark.svg
    apple_logo_light.png
    apple_icon_dark.png
```

## License

MIT — see [LICENSE](LICENSE).
