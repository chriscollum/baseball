BaseballRegression
================
Chris Collum

Install Packages if needed, and Load

``` r
# Install packages if not already present:
# install.packages(c("Lahman", "tidyverse", "broom", "pROC"))

library(Lahman)
library(tidyverse)
library(broom)
library(pROC)

# Load the Teams dataset
data("Teams")

# Convert to tibble for clean console printing
teams <- as_tibble(Teams)
```

Can we Predict if a team will win the World Series or not?

``` r
# 1. Prepare and filter data
# Focus on modern playoff-era teams (1969-present) that reached the postseason
playoff_teams <- Teams %>%
  filter(yearID >= 1969, yearID != 1994) %>% # Exclude 1994 strike (no WS)
  filter(DivWin == "Y" | WCWin == "Y") %>%
  mutate(
    # Target variable: 1 if won World Series, 0 otherwise
    WS_Winner = ifelse(WSWin == "Y", 1, 0),
    # Feature engineering from regular season metrics
    WinPct    = W / G,
    RunDiff   = R - RA,
    R_per_G   = R / G,
    RA_per_G  = RA / G,
    HR_per_G  = HR / G
  ) %>%
  select(yearID, teamID, name, WS_Winner, WinPct, RunDiff, R_per_G, RA_per_G, ERA, HR_per_G)

# 2. Time-based Train / Test Split
# Train on 1969–2010, Test on 2011–present
train_df <- playoff_teams %>% filter(yearID <= 2010)
test_df  <- playoff_teams %>% filter(yearID > 2010)

# 3. Fit a Logistic Regression Model
ws_model <- glm(
  WS_Winner ~ WinPct + RunDiff + ERA + HR_per_G,
  data = train_df,
  family = binomial(link = "logit")
)

summary(ws_model)
```

    ## 
    ## Call:
    ## glm(formula = WS_Winner ~ WinPct + RunDiff + ERA + HR_per_G, 
    ##     family = binomial(link = "logit"), data = train_df)
    ## 
    ## Coefficients:
    ##              Estimate Std. Error z value Pr(>|z|)
    ## (Intercept) -3.632532   5.178308  -0.701    0.483
    ## WinPct       6.126127   8.737698   0.701    0.483
    ## RunDiff      0.002516   0.005263   0.478    0.633
    ## ERA         -0.239294   0.545570  -0.439    0.661
    ## HR_per_G    -0.928489   1.123735  -0.826    0.409
    ## 
    ## (Dispersion parameter for binomial family taken to be 1)
    ## 
    ##     Null deviance: 216.40  on 231  degrees of freedom
    ## Residual deviance: 209.51  on 227  degrees of freedom
    ## AIC: 219.51
    ## 
    ## Number of Fisher Scoring iterations: 4

``` r
# 4. Generate Predicted Probabilities on Test Data
test_df <- test_df %>%
  mutate(pred_prob = predict(ws_model, newdata = test_df, type = "response"))

# 5. Evaluate: Pick the Favorite for Each Year
predicted_champs <- test_df %>%
  group_by(yearID) %>%
  slice_max(order_by = pred_prob, n = 1) %>%
  select(yearID, Predicted_Champ = name, pred_prob, Actual_Result = WS_Winner)

# View model selections
print(predicted_champs)
```

    ## # A tibble: 15 × 4
    ## # Groups:   yearID [15]
    ##    yearID Predicted_Champ       pred_prob Actual_Result
    ##     <int> <chr>                     <dbl>         <dbl>
    ##  1   2011 Philadelphia Phillies     0.287             0
    ##  2   2012 San Francisco Giants      0.202             1
    ##  3   2013 St. Louis Cardinals       0.263             0
    ##  4   2014 Washington Nationals      0.219             0
    ##  5   2015 St. Louis Cardinals       0.263             0
    ##  6   2016 Chicago Cubs              0.269             1
    ##  7   2017 Cleveland Indians         0.242             0
    ##  8   2018 Houston Astros            0.270             0
    ##  9   2019 Los Angeles Dodgers       0.207             0
    ## 10   2020 Los Angeles Dodgers       0.190             1
    ## 11   2021 Los Angeles Dodgers       0.264             0
    ## 12   2022 Los Angeles Dodgers       0.382             0
    ## 13   2023 Baltimore Orioles         0.187             0
    ## 14   2024 Milwaukee Brewers         0.160             0
    ## 15   2025 Milwaukee Brewers         0.207             0

``` r
# Accuracy of top pick
fav_accuracy <- mean(predicted_champs$Actual_Result == 1)
cat("Proportion of seasons where the model's top pick won the WS:", round(fav_accuracy, 3), "\n")
```

    ## Proportion of seasons where the model's top pick won the WS: 0.2

``` r
# 6. Overall Model Discrimination (ROC-AUC)
roc_obj <- roc(test_df$WS_Winner, test_df$pred_prob)
cat("Test ROC-AUC:", round(auc(roc_obj), 3), "\n")
```

    ## Test ROC-AUC: 0.653
