/**
 * QuizMaster Application Interactive Scripts
 */

document.addEventListener("DOMContentLoaded", function () {
    // 1. Auto-dismiss alerts after 5 seconds
    const alerts = document.querySelectorAll(".alert-dismissible");
    alerts.forEach(function (alert) {
        setTimeout(function () {
            const bsAlert = bootstrap.Alert.getOrCreateInstance(alert);
            if (bsAlert) bsAlert.close();
        }, 5000);
    });

    // 2. Radio Card Option Selection Highlight
    const optionCards = document.querySelectorAll(".option-card");
    optionCards.forEach(function (card) {
        const radio = card.querySelector('input[type="radio"]');
        if (radio) {
            // Initial state
            if (radio.checked) {
                card.classList.add("selected");
            }

            card.addEventListener("click", function () {
                const name = radio.name;
                const groupCards = document.querySelectorAll(`input[name="${name}"]`);
                groupCards.forEach(function (r) {
                    const parentCard = r.closest(".option-card");
                    if (parentCard) parentCard.classList.remove("selected");
                });

                radio.checked = true;
                card.classList.add("selected");

                // Update answered counter if on quiz page
                updateQuizProgress();
            });
        }
    });

    // 3. Quiz Live Countdown Timer & Answer Tracking
    const timerElement = document.getElementById("quizTimer");
    const quizForm = document.getElementById("quizForm");

    if (timerElement && quizForm) {
        const timeLimitMinutes = parseInt(timerElement.getAttribute("data-time-limit") || "10", 10);
        let totalSeconds = timeLimitMinutes * 60;

        function formatTime(seconds) {
            const m = Math.floor(seconds / 60);
            const s = seconds % 60;
            return `${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`;
        }

        timerElement.textContent = formatTime(totalSeconds);

        const timerInterval = setInterval(function () {
            totalSeconds--;
            timerElement.textContent = formatTime(totalSeconds);

            // Warning style under 60 seconds
            if (totalSeconds <= 60) {
                const timerBox = document.getElementById("timerBox");
                if (timerBox) timerBox.classList.add("timer-urgent");
            }

            if (totalSeconds <= 0) {
                clearInterval(timerInterval);
                alert("Time is up! Your quiz will now be submitted automatically.");
                quizForm.submit();
            }
        }, 1000);

        // Update initial answered count
        updateQuizProgress();

        // Quiz form submit confirmation
        quizForm.addEventListener("submit", function (e) {
            const totalQuestions = parseInt(document.getElementById("totalQuestionsCount")?.value || "0", 10);
            const answeredCount = getAnsweredQuestionsCount();

            if (answeredCount < totalQuestions) {
                const proceed = confirm(
                    `You have answered ${answeredCount} of ${totalQuestions} questions. Are you sure you want to submit now?`
                );
                if (!proceed) {
                    e.preventDefault();
                }
            }
        });
    }

    function getAnsweredQuestionsCount() {
        const checkedRadios = document.querySelectorAll('#quizForm input[type="radio"]:checked');
        return checkedRadios.length;
    }

    function updateQuizProgress() {
        const totalElem = document.getElementById("totalQuestionsCount");
        const progressElem = document.getElementById("answeredCountDisplay");
        const progressBar = document.getElementById("quizProgressBar");

        if (totalElem && progressElem && progressBar) {
            const total = parseInt(totalElem.value, 10);
            const answered = getAnsweredQuestionsCount();
            progressElem.textContent = answered;

            const percentage = total > 0 ? Math.round((answered / total) * 100) : 0;
            progressBar.style.width = `${percentage}%`;
            progressBar.setAttribute("aria-valuenow", percentage);
        }
    }

    // 4. Circular Progress Gauge Animation (Result Page)
    const circularProgress = document.getElementById("circularScoreProgress");
    if (circularProgress) {
        const percentage = parseFloat(circularProgress.getAttribute("data-percentage") || "0");
        const radius = 65;
        const circumference = 2 * Math.PI * radius;

        circularProgress.style.strokeDasharray = `${circumference}`;
        circularProgress.style.strokeDashoffset = `${circumference}`;

        // Color based on percentage
        if (percentage >= 80) {
            circularProgress.setAttribute("stroke", "#10b981");
        } else if (percentage >= 60) {
            circularProgress.setAttribute("stroke", "#4f46e5");
        } else if (percentage >= 40) {
            circularProgress.setAttribute("stroke", "#f59e0b");
        } else {
            circularProgress.setAttribute("stroke", "#ef4444");
        }

        setTimeout(function () {
            const offset = circumference - (percentage / 100) * circumference;
            circularProgress.style.strokeDashoffset = `${offset}`;
        }, 100);
    }
});
