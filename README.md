# Radio range tester
Scripts for testing range of radio transcievers

## Process
 - packet is sent once per second
 - mobile unit sends packets between 20th and 60th second
 - stabile unit sends packets between 0th and 40th second
 - time of send within the second is set by config choice `send_shift_ms`
