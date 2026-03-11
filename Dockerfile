FROM public.ecr.aws/lambda/python:3.12

# Set environment variables at build time
ENV FONTCONFIG_PATH=/etc/fonts
ENV TMPDIR=/tmp
ENV HOME=/tmp
ENV PYTHONUNBUFFERED=1

# Install system dependencies version 1 lambda
# RUN dnf install -y \
#     cairo \
#     pango \
#     gdk-pixbuf2 \
#     libffi \
#     libxml2 \
#     libxslt \
#     gcc \
#     gcc-c++ \
#     make \
#     fontconfig \        
#     freetype \          
#     libpng \            
#     libjpeg-turbo \     
#     zlib \              
#  && dnf clean all

# Install System Dependencies for lambda version 2
RUN dnf install -y \
    alsa-lib \
    atk \
    at-spi2-atk \
    cairo \
    cups-libs \
    dbus-libs \
    expat \
    flac-libs \
    gdk-pixbuf2 \
    glib2 \
    gtk3 \
    libdrm \
    libgbm \
    libX11 \
    libXcomposite \
    libXcursor \
    libXdamage \
    libXext \
    libXfixes \
    libXi \
    libXrandr \
    libXrender \
    libXScrnSaver \
    libXtst \
    mesa-libgbm \
    nspr \
    nss \
    nss-util \
    pango \
    pulseaudio-libs \
    xorg-x11-fonts-100dpi \
    xorg-x11-fonts-75dpi \
    xorg-x11-fonts-cyrillic \
    xorg-x11-fonts-misc \
    xorg-x11-fonts-Type1 \
 && dnf clean all

# Generate font cache at build time (critical for WeasyPrint)
# RUN fc-cache -fv
# Set env vars
ENV PLAYWRIGHT_BROWSERS_PATH=/opt/ms-playwright
ENV HOME=/tmp
# Copy requirements and install Python packages
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
# Install Chromium at build time into /tmp cache
# ENV PLAYWRIGHT_BROWSERS_PATH=/tmp/.cache/ms-playwright
# RUN pip install playwright && playwright install chromium
# Install playwright and chromium at build time

RUN pip install playwright==1.58.0 && \
    playwright install chromium --only-shell
# RUN PLAYWRIGHT_BROWSERS_PATH=/opt/ms-playwright playwright install chromium-1200

# Copy your source code
COPY src/ ${LAMBDA_TASK_ROOT}/

# Set the handler
CMD ["lambda_function_v2.lambda_handler"]