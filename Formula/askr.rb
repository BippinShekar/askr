class Askr < Formula
  desc "Context-aware codebase Q&A from your terminal"
  homepage "https://github.com/BippinShekar/askr"
  url "https://github.com/BippinShekar/askr/archive/refs/tags/v1.0.0.tar.gz"
  sha256 "REPLACE_WITH_SHA256_AFTER_RELEASE"
  license "MIT"

  depends_on "python@3.12"

  def install
    venv = libexec/"venv"
    system "python3", "-m", "venv", venv
    pip = venv/"bin/pip"
    system pip, "install", "--upgrade", "pip"
    system pip, "install", "anthropic", "openai", "python-dotenv", "pathspec", "rich"

    # Copy all source files into libexec
    libexec.install Dir["*.py"]

    # Write the wrapper script
    (bin/"ask").write <<~SH
      #!/bin/bash
      export ASKR_ENV="#{etc}/askr/.env"
      exec "#{venv}/bin/python" "#{libexec}/ask.py" "$@"
    SH
    chmod 0755, bin/"ask"

    # Ensure the config dir exists
    (etc/"askr").mkpath
  end

  def caveats
    <<~EOS
      To configure your API keys, run:
        ask setup

      Then in each project you want to use askr:
        ask init

      Usage:
        ask "your question"
        ask "cto: your architecture question"
        ask "debug: why is this failing"
        ask "web: what is the current price of..."
    EOS
  end

  test do
    assert_match "askr", shell_output("#{bin}/ask 2>&1", 0)
  end
end
