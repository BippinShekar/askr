class Askr < Formula
  desc "Context-aware codebase Q&A and session orchestration for Claude Code"
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
    system pip, "install", "-r", "requirements.txt"

    # Full package tree, not just the root *.py files — both entry points
    # below import from the askr/ package (cli, hooks, session, state, qa, ...).
    libexec.install "ask.py"
    libexec.install "askr"

    # ask: one-shot codebase Q&A ("ask 'why is this failing'")
    (bin/"ask").write <<~SH
      #!/bin/bash
      export ASKR_ENV="#{etc}/askr/.env"
      exec "#{venv}/bin/python" "#{libexec}/ask.py" "$@"
    SH
    chmod 0755, bin/"ask"

    # askr: session orchestration (init/status/goals/launch/uninstall/...)
    (bin/"askr").write <<~SH
      #!/bin/bash
      export ASKR_ENV="#{etc}/askr/.env"
      exec "#{venv}/bin/python" "#{libexec}/askr/cli/askr.py" "$@"
    SH
    chmod 0755, bin/"askr"

    # Ensure the config dir exists
    (etc/"askr").mkpath
  end

  def caveats
    <<~EOS
      To configure your API keys, run:
        ask setup

      Then in each project you want to use askr:
        askr init

      Usage:
        ask "your question"
        ask "cto: your architecture question"
        ask "debug: why is this failing"
        ask "web: what is the current price of..."

        askr status
        askr goals
        askr goal add "..."
    EOS
  end

  test do
    assert_match "askr", shell_output("#{bin}/ask 2>&1", 0)
    assert_match "askr", shell_output("#{bin}/askr 2>&1", 0)
  end
end
