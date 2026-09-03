# Stroop-color-word-test
A modified Stroop Color Test developed for an IRB-approved human-subject experiment in Purdue University's Snowball Lab. The task alternates between color-identification and word-identification trials to induce cognitive stress and study physiological responses associated with blood pressure changes.

This project implements a modified Stroop Color Test for use in a NIRB experiment conducted in the Snowball Lab. The Stroop test is a cognitive task that measures interference between the meaning of a word and the visual color in which that word is displayed. When the word and its displayed color conflict, participants must suppress the automatic tendency to read the word and instead respond according to the task instruction.

This experiment uses two variations of the Stroop task:

1. Color Identification (Incongruent Stroop Task)
A color word is displayed in a font color that may differ from the color named by the word. The participant must select the displayed font color, rather than the color represented by the word.

For example, if the word "BLUE" is displayed in red, the correct response is red.

2. Word Identification (Congruent Stroop Task)
A color word is displayed using the same color represented by the word. The participant must select the color indicated by the word.

For example, if "GREEN" is displayed in green, the correct response is green.

Trials from these two conditions are presented in randomized order. The task is designed to introduce cognitive demand and stress as part of the NIRB experimental protocol in the Snowball Lab, where physiological responses such as changes related to blood pressure can be studied.

The experiment uses a dual-monitor setup. One monitor presents the Stroop task to the participant, while a second monitor provides the experiment observer with information about the participant's responses. When an incorrect response occurs, the program produces an audible beep and pauses the task. The observer can then provide the standardized experimental feedback before allowing the participant to continue.

The system also records trial information such as the Stroop condition, stimulus, participant response, response accuracy, reaction time, and relevant event timestamps for subsequent analysis with physiological measurements.
